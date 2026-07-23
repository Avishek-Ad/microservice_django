import json
import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase
from recruitment.models import JobPosting, AdminApplicationReview, ProcessedEvent
from recruitment.management.commands.kafka_consumer import Command 

class KafkaConsumerCommandTest(TestCase):
    
    def setUp(self):
        """Set up initial test data."""
        self.command = Command()
        self.command.stdout = MagicMock()  # Suppress console output during tests
        self.command.stderr = MagicMock()  # Suppress console error output during tests

        self.job = JobPosting.objects.create(
            title="Senior Backend Engineer",
            is_active=True
        )
        
        self.valid_event_id = str(uuid.uuid4())
        self.valid_payload = {
            "event_id": self.valid_event_id,
            "event": "application_created",
            "user_application_id": 99,
            "candidate_name": "Sita Sharma",
            "candidate_email": "sita@example.com",
            "job_id": self.job.id,
            "resume_url": "https://example.com/resume.pdf"
        }

    def _get_mock_message(self, payload):
        """Helper function to create a mock confluent_kafka message."""
        mock_msg = MagicMock()
        mock_msg.key.return_value = b"test-key"
        mock_msg.value.return_value = json.dumps(payload).encode('utf-8') if payload else None
        mock_msg.topic.return_value = "user_events"
        mock_msg.partition.return_value = 0
        mock_msg.error.return_value = None
        return mock_msg

    # TEST GRACEFUL SHUTDOWN SIGNAL
    def test_handle_shutdown_signal(self):
        """Verify shutdown signal sets the flag to break the while loop."""
        self.assertFalse(self.command.shutdown_requested)
        self.command.handle_shutdown(signum=2, frame=None)
        self.assertTrue(self.command.shutdown_requested)

    # TEST EVENT HANDLER LOGIC (handle_application_created_event)
    def test_handle_application_created_event_success(self):
        """Verify processing a valid application creation payload creates DB records."""
        self.command.handle_application_created_event(self.valid_payload)
        
        # Verify the record was created
        review = AdminApplicationReview.objects.get(user_application_id=99)
        self.assertEqual(review.candidate_name, "Sita Sharma")
        self.assertEqual(review.job.id, self.job.id)

    def test_handle_application_created_event_missing_job(self):
        """Verify missing job_id does not crash the consumer but logs a warning."""
        invalid_payload = self.valid_payload.copy()
        invalid_payload['job_id'] = 999999  # Job does not exist
        
        # Should not raise exception
        self.command.handle_application_created_event(invalid_payload)
        
        # Verify no review was created
        self.assertEqual(AdminApplicationReview.objects.count(), 0)

    # TEST MESSAGE PROCESSING & IDEMPOTENCY
    def test_process_message_happy_path(self):
        """Verify a new valid message is processed, tracked, and committed."""
        mock_msg = self._get_mock_message(self.valid_payload)
        mock_consumer = MagicMock()

        self.command.process_message(mock_msg, mock_consumer)

        # Assert idempotency tracker was created
        self.assertTrue(ProcessedEvent.objects.filter(event_id=self.valid_event_id).exists())
        
        # Assert application review was created
        self.assertTrue(AdminApplicationReview.objects.filter(user_application_id=99).exists())
        
        # Assert consumer offset was committed
        mock_consumer.commit.assert_called_once_with(mock_msg, asynchronous=False)

    def test_process_message_idempotency_skip_duplicate(self):
        """Verify an already processed event is safely skipped and still committed."""
        # Pre-create the processed event to simulate a duplicate message delivery
        ProcessedEvent.objects.create(event_id=self.valid_event_id)
        
        mock_msg = self._get_mock_message(self.valid_payload)
        mock_consumer = MagicMock()

        # Execute
        self.command.process_message(mock_msg, mock_consumer)

        # Application should NOT be created again
        self.assertEqual(AdminApplicationReview.objects.count(), 0)
        
        # Consumer MUST STILL COMMIT to move past this offset
        mock_consumer.commit.assert_called_once_with(mock_msg, asynchronous=False)

    def test_process_message_unknown_event(self):
        """Verify unknown events are logged and committed, but not processed."""
        unknown_event_id = str(uuid.uuid4())
        unknown_payload = {"event_id": unknown_event_id, "event": "some_random_event"}
        mock_msg = self._get_mock_message(unknown_payload)
        mock_consumer = MagicMock()

        self.command.process_message(mock_msg, mock_consumer)

        # ProcessedEvent should be recorded so we don't try it again
        self.assertTrue(ProcessedEvent.objects.filter(event_id=unknown_event_id).exists())
        
        # Offset should be committed
        mock_consumer.commit.assert_called_once()

    # TEST ERROR HANDLING & DATABASE ROLLBACK
    @patch.object(Command, 'handle_application_created_event')
    def test_process_message_rolls_back_tracking_on_failure(self, mock_handler):
        """Verify that if the handler crashes, ProcessedEvent is deleted so it can retry."""
        mock_handler.side_effect = Exception("Simulated DB Crash")
        
        mock_msg = self._get_mock_message(self.valid_payload)
        mock_consumer = MagicMock()

        # Process message
        self.command.process_message(mock_msg, mock_consumer)

        # Tracking event should have been rolled back (deleted)
        self.assertFalse(ProcessedEvent.objects.filter(event_id=self.valid_event_id).exists())
        
        # Offset MUST NOT be committed, so Kafka re-delivers it later
        mock_consumer.commit.assert_not_called()

    # TEST THE MAIN RUN LOOP
    @patch('recruitment.management.commands.kafka_consumer.Consumer')  # Update path
    def test_main_handle_loop_initialization_and_exit(self, mock_consumer_class):
        """Verify the command initializes Kafka, subscribes, and exits cleanly when requested."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        
        # Simulate the poll blocking, then trigger the shutdown flag to break the while loop
        def mock_poll(timeout):
            self.command.shutdown_requested = True  # Break the loop on first poll
            return None
        
        mock_consumer.poll.side_effect = mock_poll

        # Run command logic
        self.command.handle()

        # Verify Kafka initialization sequence
        mock_consumer_class.assert_called_once()
        mock_consumer.subscribe.assert_called_once_with(['user_events'])
        mock_consumer.close.assert_called_once()