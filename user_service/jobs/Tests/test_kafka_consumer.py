import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from django.core.management import call_command
from django.test import TestCase
from confluent_kafka import KafkaError

from jobs.models import JobApplication, JobApplicationStatus, ProcessedEvent, CandidateProfile
from jobs.management.commands.kafka_consumer import Command


class ConsumeKafkaEventsCommandTest(TestCase):

    def setUp(self):
        # Create dummy candidate and job application for testing status updates
        self.candidate = CandidateProfile.objects.create(
            email="jane@example.com",
            full_name="Jane Doe",
            skills="Python, Django"
        )
        self.application = JobApplication.objects.create(
            candidate=self.candidate,
            job_id=101,
            status=JobApplicationStatus.PENDING if hasattr(JobApplicationStatus, 'PENDING') else "pending"
        )

    def create_mock_kafka_message(self, payload_dict, key="test-key", topic="admin_events", partition=0, error=None):
        """Helper to build a fake confluent_kafka Message object."""
        mock_msg = MagicMock()
        mock_msg.error.return_value = error
        mock_msg.topic.return_value = topic
        mock_msg.partition.return_value = partition
        
        if key:
            mock_msg.key.return_value = key.encode("utf-8")
        else:
            mock_msg.key.return_value = None

        if payload_dict is not None:
            mock_msg.value.return_value = json.dumps(payload_dict).encode("utf-8")
        else:
            mock_msg.value.return_value = None

        return mock_msg

    # Test Event Handlers Individually
    @patch("jobs.management.commands.kafka_consumer.async_to_sync")
    @patch("jobs.management.commands.kafka_consumer.get_channel_layer")
    @patch("sys.stdout")
    def test_handle_application_status_update_hired(
        self, mock_stdout, mock_get_channel_layer, mock_async_to_sync
    ):
        """Test status update event changes DB status and broadcasts to Channels."""
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer

        # Dummy function to capture what async_to_sync wraps and calls
        mock_broadcast = MagicMock()
        mock_async_to_sync.return_value = mock_broadcast

        cmd = Command()
        payload = {
            "user_application_id": self.application.id,
            "new_status": "hired"
        }

        cmd.handle_application_status_update(payload)

        # 1. Check DB state update
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, JobApplicationStatus.APPROVED)

        # 2. Verify async_to_sync was called with channel_layer.group_send
        mock_async_to_sync.assert_called_once_with(mock_channel_layer.group_send)

        # 3. Verify the sync-wrapped function was called with the notification payload
        mock_broadcast.assert_called_once_with(
            "user_notification_room",
            {
                "type": "send_notification",
                "message": f"Admin Hired {self.candidate.full_name} for job with id {self.application.job_id}",
            }
        )
    @patch("jobs.management.commands.kafka_consumer.get_opensearch_client")
    def test_handle_index_or_update_document(self, mock_get_opensearch_client):
        """Test syncing a job document to OpenSearch."""
        mock_os_client = MagicMock()
        mock_get_opensearch_client.return_value = mock_os_client

        cmd = Command()
        payload = {
            "job_id": 101,
            "title": "Backend Engineer",
            "description": "Django developer required",
            "department": "Engineering",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z"
        }

        cmd.handle_index_or_update_document(payload)

        mock_os_client.index.assert_called_once_with(
            index="jobs",
            id="101",
            body={
                "id": 101,
                "title": "Backend Engineer",
                "description": "Django developer required",
                "department": "Engineering",
                "is_active": True,
                "created_at": "2026-01-01T00:00:00Z"
            },
            refresh=True
        )

    @patch("jobs.management.commands.kafka_consumer.get_opensearch_client")
    def test_handle_delete_document(self, mock_get_opensearch_client):
        """Test deleting a job document from OpenSearch when it exists."""
        mock_os_client = MagicMock()
        mock_os_client.exists.return_value = True
        mock_get_opensearch_client.return_value = mock_os_client

        cmd = Command()
        payload = {"job_id": 101}

        cmd.handle_delete_document(payload)

        mock_os_client.exists.assert_called_once_with(index="jobs", id="101")
        mock_os_client.delete.assert_called_once_with(index="jobs", id="101")

    # Test Idempotency and Rollback Logic
    def test_process_message_idempotency(self):
        """Test duplicate messages are skipped when ProcessedEvent exists."""
        event_id = str(uuid.uuid4())
        ProcessedEvent.objects.create(event_id=event_id)

        mock_msg = self.create_mock_kafka_message({
            "event_id": event_id,
            "event": "job_deleted",
            "job_id": 101
        })
        mock_consumer = MagicMock()

        cmd = Command()
        cmd.process_message(mock_msg, mock_consumer)

        # Ensure message offset was committed and skipped without processing again
        mock_consumer.commit.assert_called_once_with(mock_msg, asynchronous=False)

    @patch.object(Command, "handle_application_status_update", side_effect=Exception("DB connection error"))
    def test_process_message_rollback_on_failure(self, mock_handler):
        """Test ProcessedEvent tracking is deleted if message processing raises an exception."""
        valid_event_id = str(uuid.uuid4())
        mock_msg = self.create_mock_kafka_message({
            "event_id": valid_event_id,
            "event": "application_status_update",
            "user_application_id": self.application.id,
            "new_status": "hired"
        })
        mock_consumer = MagicMock()

        cmd = Command()
        cmd.process_message(mock_msg, mock_consumer)

        # ProcessedEvent should NOT exist due to exception rollback
        self.assertFalse(ProcessedEvent.objects.filter(event_id=valid_event_id).exists())

    # Test Consumer Event Loop Run via management command
    @patch("jobs.management.commands.kafka_consumer.Consumer")
    @patch("jobs.management.commands.kafka_consumer.get_opensearch_client")
    def test_command_loop_execution_and_graceful_shutdown(self, mock_get_os_client, mock_kafka_consumer_cls):
        """Test running the command loop through poll ticks and trigger graceful shutdown."""
        mock_consumer = MagicMock()
        mock_kafka_consumer_cls.return_value = mock_consumer
        
        valid_event_id = str(uuid.uuid4())
        mock_msg = self.create_mock_kafka_message({
            "event_id": valid_event_id,
            "event": "job_deleted",
            "job_id": 101
        })

        # Side effect sequence: return 1 message, then trigger shutdown request on next tick
        def poll_side_effect(timeout):
            # Request shutdown on the second poll call to break loop
            cmd.shutdown_requested = True
            return mock_msg

        mock_consumer.poll.side_effect = poll_side_effect

        cmd = Command()
        cmd.handle()

        # Check subscriptions and clean consumer close
        mock_consumer.subscribe.assert_called_once_with(["admin_events"])
        mock_consumer.close.assert_called_once()
        self.assertTrue(ProcessedEvent.objects.filter(event_id=valid_event_id).exists())