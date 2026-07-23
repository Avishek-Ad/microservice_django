from unittest.mock import MagicMock, patch
from django.test import TestCase

from jobs.models import PublishedEvent
from jobs.tasks import publishing_events_in_db_to_kafka


class PublishingEventsTaskTest(TestCase):

    def setUp(self):
        # Create unconsumed events in the database for testing
        self.event1 = PublishedEvent.objects.create(
            channel="user_events",
            payload={"event": "application_created", "user_application_id": 1},
            extra={"sender": "user_service"},
            is_consumed=False,
        )
        self.event2 = PublishedEvent.objects.create(
            channel="user_events",
            payload={"event": "application_created", "user_application_id": 2},
            extra={"sender": "user_service"},
            is_consumed=False,
        )

    @patch("jobs.tasks.get_kafka_producer")
    def test_publish_events_success(self, mock_get_kafka_producer):
        """Test happy path: events are successfully published and marked as consumed."""
        # Setup mock producer
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0  # 0 unflushed means successfully flushed
        mock_get_kafka_producer.return_value = mock_producer

        # Run the Celery task directly in-process
        result = publishing_events_in_db_to_kafka()

        # Assert return value
        self.assertEqual(result, "Successfully Published 2 events one-by-line")

        # Verify Kafka produce calls
        self.assertEqual(mock_producer.produce.call_count, 2)
        self.assertEqual(mock_producer.flush.call_count, 2)

        # Verify DB updates
        self.event1.refresh_from_db()
        self.event2.refresh_from_db()
        self.assertTrue(self.event1.is_consumed)
        self.assertTrue(self.event2.is_consumed)

    @patch("jobs.tasks.get_kafka_producer")
    def test_no_unconsumed_events(self, mock_get_kafka_producer):
        """Test behavior when no unconsumed events are present in the DB."""
        # Mark existing setup events as consumed
        PublishedEvent.objects.update(is_consumed=True)

        result = publishing_events_in_db_to_kafka()

        self.assertEqual(result, "No New Events found")
        # Ensure producer was never called
        mock_get_kafka_producer.assert_called_once()
        mock_producer = mock_get_kafka_producer.return_value
        mock_producer.produce.assert_not_called()

    @patch("jobs.tasks.get_kafka_producer")
    def test_flush_failure_skips_db_update(self, mock_get_kafka_producer):
        """Test that if producer.flush() returns > 0 (timeout/failure), DB is NOT updated."""
        mock_producer = MagicMock()
        # Simulate flush failure: 1 message remained unflushed
        mock_producer.flush.return_value = 1
        mock_get_kafka_producer.return_value = mock_producer

        result = publishing_events_in_db_to_kafka()

        self.assertEqual(result, "Successfully Published 0 events one-by-line")

        # Verify DB records remain unconsumed
        self.event1.refresh_from_db()
        self.event2.refresh_from_db()
        self.assertFalse(self.event1.is_consumed)
        self.assertFalse(self.event2.is_consumed)

    @patch("jobs.tasks.get_kafka_producer")
    def test_producer_produce_exception_handling(self, mock_get_kafka_producer):
        """Test task resilience when producer.produce raises an Exception."""
        mock_producer = MagicMock()
        mock_producer.produce.side_effect = Exception("Kafka connection error")
        mock_get_kafka_producer.return_value = mock_producer

        result = publishing_events_in_db_to_kafka()

        # Task should catch the exception gracefully and process 0 successful
        self.assertEqual(result, "Successfully Published 0 events one-by-line")

        # Verify DB records remain unconsumed
        self.event1.refresh_from_db()
        self.assertFalse(self.event1.is_consumed)
