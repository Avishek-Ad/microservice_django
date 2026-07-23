import json
from unittest import TestCase
from unittest.mock import patch, MagicMock
from confluent_kafka import KafkaError
from logs.management.commands.kafka_consumer import Command


class AuditKafkaConsumerCommandTest(TestCase):

    def setUp(self):
        """Set up initial test environment and fixtures."""
        self.command = Command()
        self.command.stdout = MagicMock()
        self.command.stderr = MagicMock()

        self.valid_event_id = "audit-evt-12345"
        self.valid_payload = {
            "event_id": self.valid_event_id,
            "event": "application_created",
            "user_application_id": 99,
            "extra": {
                "log_type": "AUDIT",
                "sender": "recruitment_service",
                "receiver": "audit_service",
                "event_type": "APPLICATION_SUBMITTED",
                "occured_at": "2026-03-30T10:00:00Z"
            }
        }

    def _get_mock_message(self, payload=None, error=None, key=b"test-key", topic="audit_events", partition=0):
        """Helper to build a mock confluent_kafka Message object."""
        mock_msg = MagicMock()
        mock_msg.key.return_value = key
        mock_msg.value.return_value = json.dumps(payload).encode('utf-8') if payload is not None else None
        mock_msg.topic.return_value = topic
        mock_msg.partition.return_value = partition
        mock_msg.error.return_value = error
        return mock_msg

    # SHUTDOWN SIGNAL TEST
    def test_handle_shutdown_signal(self):
        """Verify handling SIGINT/SIGTERM sets the graceful shutdown flag."""
        self.assertFalse(self.command.shutdown_requested)
        self.command.handle_shutdown(signum=2, frame=None)
        self.assertTrue(self.command.shutdown_requested)

    # EVENT HANDLER TESTS (handle_application_created_event)
    @patch('logs.models.SystemLog.update_one')
    def test_handle_application_created_event_success(self, mock_update_one):
        """Verify valid event payloads are correctly extracted and upserted into SystemLog."""
        self.command.handle_application_created_event(self.valid_payload)

        # Expected mongo document structure without the 'extra' key inside 'payload'
        expected_remaining_payload = {
            "event_id": self.valid_event_id,
            "event": "application_created",
            "user_application_id": 99
        }

        mock_update_one.assert_called_once_with(
            {"event_id": self.valid_event_id},
            {
                "$set": {
                    "log_type": "AUDIT",
                    "sender": "recruitment_service",
                    "receiver": "audit_service",
                    "event_type": "APPLICATION_SUBMITTED",
                    "payload": expected_remaining_payload,
                    "occured_at": "2026-03-30T10:00:00Z"
                }
            },
            upsert=True
        )

    @patch('logs.models.SystemLog.update_one')
    def test_handle_application_created_event_missing_event_id(self, mock_update_one):
        """Verify missing event_id logs an error and skips updating SystemLog."""
        invalid_payload = self.valid_payload.copy()
        invalid_payload.pop("event_id")

        self.command.handle_application_created_event(invalid_payload)

        mock_update_one.assert_not_called()
        self.command.stderr.write.assert_called_once()

    # MESSAGE PROCESSING TESTS (process_message)
    @patch.object(Command, 'handle_application_created_event')
    def test_process_message_known_event_commits(self, mock_handler):
        """Verify recognized events call the handler and perform a sync commit."""
        mock_msg = self._get_mock_message(payload=self.valid_payload)
        mock_consumer = MagicMock()

        self.command.process_message(mock_msg, mock_consumer)

        mock_handler.assert_called_once_with(self.valid_payload)
        mock_consumer.commit.assert_called_once_with(mock_msg, asynchronous=False)

    @patch.object(Command, 'handle_application_created_event')
    def test_process_message_unknown_event_commits_without_handling(self, mock_handler):
        """Verify unknown events are skipped but still committed so the consumer moves forward."""
        unknown_payload = {"event_id": "evt-999", "event": "untracked_event_type"}
        mock_msg = self._get_mock_message(payload=unknown_payload)
        mock_consumer = MagicMock()

        self.command.process_message(mock_msg, mock_consumer)

        mock_handler.assert_not_called()
        mock_consumer.commit.assert_called_once_with(mock_msg, asynchronous=False)

    def test_process_message_invalid_json_does_not_crash(self):
        """Verify malformed JSON payloads are caught safely and stderr is written to."""
        mock_msg = MagicMock()
        mock_msg.key.return_value = b"key"
        mock_msg.value.return_value = b"{ invalid_json_string "
        mock_consumer = MagicMock()

        # Should handle JSONDecodeError internally without raising
        self.command.process_message(mock_msg, mock_consumer)

        self.command.stderr.write.assert_called_once()
        mock_consumer.commit.assert_not_called()

    # MAIN CONSUMER LOOP TESTS (handle)
    @patch('logs.management.commands.kafka_consumer.Consumer')
    @patch.object(Command, 'process_message')
    def test_handle_loop_processes_messages_and_shuts_down(self, mock_process_message, mock_consumer_class):
        """Verify subscriber connects to all 3 topics and processes messages in the poll loop."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        mock_msg = self._get_mock_message(payload=self.valid_payload)

        # First poll returns message, second poll sets shutdown flag and returns None
        def mock_poll(timeout):
            if mock_process_message.call_count == 0:
                return mock_msg
            self.command.shutdown_requested = True
            return None

        mock_consumer.poll.side_effect = mock_poll

        self.command.handle()

        mock_consumer.subscribe.assert_called_once_with(['admin_events', 'user_events', 'audit_events'])
        mock_process_message.assert_called_once_with(mock_msg, mock_consumer)
        mock_consumer.close.assert_called_once()

    @patch('logs.management.commands.kafka_consumer.Consumer')
    def test_handle_loop_kafka_partition_eof_handled_gracefully(self, mock_consumer_class):
        """Verify KafkaError._PARTITION_EOF is caught and logged without breaking consumer loop."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        mock_kafka_err = MagicMock()
        mock_kafka_err.code.return_value = KafkaError._PARTITION_EOF
        mock_eof_msg = self._get_mock_message(error=mock_kafka_err)

        def mock_poll(timeout):
            self.command.shutdown_requested = True
            return mock_eof_msg

        mock_consumer.poll.side_effect = mock_poll

        self.command.handle()

        mock_consumer.close.assert_called_once()

    @patch('logs.management.commands.kafka_consumer.Consumer')
    def test_handle_loop_kafka_unknown_topic_handled_gracefully(self, mock_consumer_class):
        """Verify UNKNOWN_TOPIC_OR_PART error logs warning and continues polling."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer

        mock_kafka_err = MagicMock()
        mock_kafka_err.code.return_value = KafkaError.UNKNOWN_TOPIC_OR_PART
        mock_err_msg = self._get_mock_message(error=mock_kafka_err)

        def mock_poll(timeout):
            self.command.shutdown_requested = True
            return mock_err_msg

        mock_consumer.poll.side_effect = mock_poll

        self.command.handle()

        mock_consumer.close.assert_called_once()