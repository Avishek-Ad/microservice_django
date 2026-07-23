from unittest import TestCase
from unittest.mock import patch, MagicMock
from bson import ObjectId
from rest_framework.test import APIRequestFactory
from rest_framework import status
from logs.views import ListLogAPIView


class ListLogAPIViewTest(TestCase):

    def setUp(self):
        """Set up test environment and helpers."""
        self.factory = APIRequestFactory()
        self.view = ListLogAPIView.as_view()

        # Mock PyMongo Documents
        self.mock_doc_1 = {
            "_id": ObjectId("65f123456789abcdef123456"),
            "event_type": "APPLICATION_SUBMITTED",
            "occured_at": "2026-03-30T10:00:00Z"
        }
        self.mock_doc_2 = {
            "_id": ObjectId("65f123456789abcdef123457"),
            "event_type": "JOB_CREATED",
            "occured_at": "2026-03-29T10:00:00Z"
        }

    def _setup_mock_cursor(self, mock_find, return_docs):
        """Helper to set up chained PyMongo cursor methods (.sort().skip().limit())."""
        mock_cursor = MagicMock()
        
        # Enable iteration over return_docs
        mock_cursor.__iter__.return_value = iter(return_docs)
        
        # Chained methods return the cursor instance
        mock_find.return_value.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        
        return mock_cursor

    # SUCCESS & PAGINATION TESTS
    @patch('logs.views.SystemLog.find')
    def test_get_logs_default_pagination(self, mock_find):
        """Verify fetching logs with default pagination (page=1, size=2) converts ObjectId to str."""
        mock_cursor = self._setup_mock_cursor(mock_find, [self.mock_doc_1, self.mock_doc_2])

        request = self.factory.get('/api/logs/')
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify pagination math: offset = (1 - 1) * 2 = 0
        mock_cursor.skip.assert_called_once_with(0)
        mock_cursor.limit.assert_called_once_with(2)

        # Verify ObjectId conversion to string in response payload
        results = response.data['results']
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['_id'], "65f123456789abcdef123456")
        self.assertEqual(results[1]['_id'], "65f123456789abcdef123457")

    @patch('logs.views.SystemLog.find')
    def test_get_logs_custom_page_and_size(self, mock_find):
        """Verify custom query parameters page=3 and size=5 calculate offset correctly."""
        mock_cursor = self._setup_mock_cursor(mock_find, [self.mock_doc_1])

        request = self.factory.get('/api/logs/?page=3&size=5')
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify pagination math: offset = (3 - 1) * 5 = 10
        mock_cursor.skip.assert_called_once_with(10)
        mock_cursor.limit.assert_called_once_with(5)

    # EDGE CASES & DEFENSIVE INPUT HANDLERS
    @patch('logs.views.SystemLog.find')
    def test_get_logs_negative_or_zero_queryParams_clamped_to_one(self, mock_find):
        """Verify negative or zero page and size parameters default safely to 1."""
        mock_cursor = self._setup_mock_cursor(mock_find, [])

        request = self.factory.get('/api/logs/?page=-5&size=0')
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # page_number = max(1, -5) -> 1; page_size = max(1, 0) -> 1
        # offset = (1 - 1) * 1 = 0
        mock_cursor.skip.assert_called_once_with(0)
        mock_cursor.limit.assert_called_once_with(1)

    @patch('logs.views.SystemLog.find')
    def test_get_logs_doc_without_object_id_handled_gracefully(self, mock_find):
        """Verify documents without an '_id' key are handled without throwing KeyError."""
        doc_no_id = {"event_type": "SYSTEM_BOOT", "occured_at": "2026-03-30T10:00:00Z"}
        self._setup_mock_cursor(mock_find, [doc_no_id])

        request = self.factory.get('/api/logs/')
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'], [doc_no_id])

    @patch('logs.views.SystemLog.find')
    def test_get_logs_empty_result_returns_empty_list(self, mock_find):
        """Verify an empty database collection returns an empty list in response."""
        self._setup_mock_cursor(mock_find, [])

        request = self.factory.get('/api/logs/')
        response = self.view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {'results': []})