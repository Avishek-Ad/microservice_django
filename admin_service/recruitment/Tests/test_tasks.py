import json
from unittest.mock import patch, MagicMock
from django.test import TestCase
from recruitment.models import PublishedEvent
from recruitment.tasks import publishing_events_in_db_to_kafka


class PublishingEventsInDbToKafkaTaskTest(TestCase):

    def setUp(self):
        """Set up test data before each test method."""
        self.event1 = PublishedEvent.objects.create(
            channel="admin_events",
            payload={"event": "job_created", "job_id": 1},
            extra={"sender": "admin_service"},
            is_consumed=False
        )
        self.event2 = PublishedEvent.objects.create(
            channel="admin_events",
            payload={"event": "job_updated", "job_id": 1},
            extra={"sender": "admin_service"},
            is_consumed=False
        )

    @patch("recruitment.tasks.get_kafka_producer")
    def test_publishing_events_success(self, mock_get_kafka_producer):
        """Verify unconsumed events are produced to Kafka and marked as consumed."""
        # Setup Mock Producer
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0  # 0 unflushed messages means success
        mock_get_kafka_producer.return_value = mock_producer

        # Execute task directly (synchronously)
        result = publishing_events_in_db_to_kafka()

        # Check return value
        self.assertEqual(result, "Successfully Published 2 events one-by-line")

        # Verify DB updates: both events should now be is_consumed=True
        self.event1.refresh_from_db()
        self.event2.refresh_from_db()
        self.assertTrue(self.event1.is_consumed)
        self.assertTrue(self.event2.is_consumed)

        # Verify producer.produce was called twice
        self.assertEqual(mock_producer.produce.call_count, 2)
        
        # Inspect payload sent to Kafka for event1
        first_call_kwargs = mock_producer.produce.call_args_list[0][1]
        self.assertEqual(first_call_kwargs["topic"], "admin_events")
        
        expected_payload = {
            "event": "job_created",
            "job_id": 1,
            "extra": {"sender": "admin_service"}
        }
        actual_payload = json.loads(first_call_kwargs["value"].decode("utf-8"))
        self.assertEqual(actual_payload, expected_payload)

    @patch("recruitment.tasks.get_kafka_producer")
    def test_no_unconsumed_events(self, mock_get_kafka_producer):
        """Verify task early-returns when no unconsumed events exist."""
        # Mark existing setup events as already consumed
        PublishedEvent.objects.update(is_consumed=True)

        mock_producer = MagicMock()
        mock_get_kafka_producer.return_value = mock_producer

        result = publishing_events_in_db_to_kafka()

        self.assertEqual(result, "No New Events found")
        # Ensure produce was never called
        mock_producer.produce.assert_not_called()

    @patch("recruitment.tasks.get_kafka_producer")
    def test_kafka_flush_failure_skips_db_update(self, mock_get_kafka_producer):
        """Verify DB event is NOT marked as consumed if producer.flush() fails."""
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 1  # Simulated failure: 1 message failed to flush
        mock_get_kafka_producer.return_value = mock_producer

        result = publishing_events_in_db_to_kafka()

        # Result should indicate 0 published events
        self.assertEqual(result, "Successfully Published 0 events one-by-line")

        # Events should remain unconsumed in DB
        self.event1.refresh_from_db()
        self.event2.refresh_from_db()
        self.assertFalse(self.event1.is_consumed)
        self.assertFalse(self.event2.is_consumed)

    @patch("recruitment.tasks.get_kafka_producer")
    def test_kafka_producer_exception_handling(self, mock_get_kafka_producer):
        """Verify that an exception on one event doesn't crash the loop for other events."""
        mock_producer = MagicMock()
        # Raise exception on first call, succeed on second call
        mock_producer.produce.side_effect = [Exception("Kafka Connection Timeout"), None]
        mock_producer.flush.return_value = 0
        mock_get_kafka_producer.return_value = mock_producer

        result = publishing_events_in_db_to_kafka()

        # 1 failed, 1 succeeded
        self.assertEqual(result, "Successfully Published 1 events one-by-line")

        # Event 1 failed -> remains is_consumed=False
        self.event1.refresh_from_db()
        self.assertFalse(self.event1.is_consumed)

        # Event 2 succeeded -> updated to is_consumed=True
        self.event2.refresh_from_db()
        self.assertTrue(self.event2.is_consumed)

    @patch("recruitment.tasks.get_kafka_producer")
    def test_batch_limit_to_50_records(self, mock_get_kafka_producer):
        """Verify task only picks up a maximum of 50 events per batch."""
        # Create 55 events in total (2 from setUp + 53 more)
        for i in range(53):
            PublishedEvent.objects.create(
                channel="admin_events",
                payload={"event": f"event_{i}"},
                is_consumed=False
            )

        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0
        mock_get_kafka_producer.return_value = mock_producer

        result = publishing_events_in_db_to_kafka()

        # Should process exactly 50 events
        self.assertEqual(result, "Successfully Published 50 events one-by-line")
        self.assertEqual(PublishedEvent.objects.filter(is_consumed=True).count(), 50)
        self.assertEqual(PublishedEvent.objects.filter(is_consumed=False).count(), 5)