from unittest.mock import patch, MagicMock
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, override_settings
from django.conf import settings
import requests
from django.core.files.storage import InMemoryStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from jobs.models import CandidateProfile, JobApplication, PublishedEvent

class JobSearchAPIViewTest(APITestCase):
    def setUp(self):
        self.url = reverse("job-search")

        # Mock OpenSearch hits structure matching your index properties
        self.mock_hits = [
            {
                "_score": 1.85,
                "_source": {
                    "id": 1,
                    "title": "Senior Python Engineer",
                    "description": "Looking for Django and REST API expertise.",
                    "department": "Engineering",
                    "is_active": True,
                    "created_at": "2026-07-20T10:00:00Z",
                },
            },
            {
                "_score": 1.20,
                "_source": {
                    "id": 2,
                    "title": "Frontend Developer",
                    "description": "React developer to work on modern UI dashboards.",
                    "department": "Engineering",
                    "is_active": True,
                    "created_at": "2026-07-21T12:30:00Z",
                },
            },
        ]

    @patch("jobs.views.get_opensearch_client")
    def test_search_jobs_default_returns_active_jobs(self, mock_get_client):
        # Setup mock client search response
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": self.mock_hits}}
        mock_get_client.return_value = mock_client

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        
        # Verify hit structure and score injection
        first_result = response.data["results"][0]
        self.assertEqual(first_result["id"], 1)
        self.assertEqual(first_result["title"], "Senior Python Engineer")
        self.assertEqual(first_result["department"], "Engineering")
        self.assertEqual(first_result["_score"], 1.85)

        # Verify default query filters for is_active: True
        mock_client.search.assert_called_once()
        call_kwargs = mock_client.search.call_args[1]
        self.assertEqual(call_kwargs["index"], "jobs")
        self.assertEqual(
            call_kwargs["body"]["query"]["bool"]["must"],
            [{"term": {"is_active": True}}]
        )

    @patch("jobs.views.get_opensearch_client")
    def test_search_jobs_with_q_and_department_filters(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": [self.mock_hits[0]]}}
        mock_get_client.return_value = mock_client

        query_params = {"q": "Python", "department": "Engineering"}
        response = self.client.get(self.url, query_params)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        # Inspect the constructed search_body sent to OpenSearch
        search_body = mock_client.search.call_args[1]["body"]
        must_clauses = search_body["query"]["bool"]["must"]

        self.assertEqual(len(must_clauses), 3)
        self.assertIn({"term": {"is_active": True}}, must_clauses)
        self.assertIn({"term": {"department": "Engineering"}}, must_clauses)
        self.assertIn(
            {
                "multi_match": {
                    "query": "Python",
                    "fields": ["title^2", "description"],
                    "fuzziness": "AUTO",
                }
            },
            must_clauses,
        )

    @patch("jobs.views.get_opensearch_client")
    def test_search_jobs_no_matches_returns_empty_list(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search.return_value = {"hits": {"hits": []}}
        mock_get_client.return_value = mock_client

        response = self.client.get(self.url, {"q": "DevOps"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    @patch("jobs.views.get_opensearch_client")
    def test_search_jobs_opensearch_exception_returns_500(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("OpenSearch connection timeout")
        mock_get_client.return_value = mock_client

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"], "OpenSearch connection timeout")
        

class JobListAPIViewTest(APITestCase):
    def setUp(self):
        self.url = reverse("job-list")
        self.expected_admin_url = f"{settings.ADMIN_MICROSERVICE_URL}/api/posted_jobs/"

    @patch("jobs.views.requests.get")
    def test_get_posted_jobs_success(self, mock_requests_get):
        # Arrange mock response from Admin Microservice
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_200_OK
        mock_data = {
            "results": [
                {
                    "id": 1,
                    "title": "Backend Developer",
                    "department": "Engineering",
                    "is_active": True,
                },
                {
                    "id": 2,
                    "title": "UI/UX Designer",
                    "department": "Design",
                    "is_active": True,
                },
            ]
        }
        mock_response.json.return_value = mock_data
        mock_requests_get.return_value = mock_response

        # Act
        response = self.client.get(self.url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, mock_data)
        mock_requests_get.assert_called_once_with(self.expected_admin_url, timeout=5)

    @patch("jobs.views.requests.get")
    def test_get_posted_jobs_admin_service_error_status(self, mock_requests_get):
        # Simulate Admin Microservice returning a 500 error
        mock_response = MagicMock()
        mock_response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        mock_requests_get.return_value = mock_response

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.data,
            {"error": "Admin service failed to provide data"}
        )
        mock_requests_get.assert_called_once_with(self.expected_admin_url, timeout=5)

    @patch("jobs.views.requests.get")
    def test_get_posted_jobs_admin_service_unreachable(self, mock_requests_get):
        # Simulate a network error / timeout connecting to Admin Microservice
        mock_requests_get.side_effect = requests.exceptions.RequestException("Connection refused")

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.data,
            {"error": "Admin microservice is currently unreachable"}
        )
        mock_requests_get.assert_called_once_with(self.expected_admin_url, timeout=5)
        

# @override_settings(STORAGES={
#     "default": {
#         "BACKEND": "django.core.files.storage.InMemoryStorage",
#     }
# })
# class ApplyJobAPIViewTest(APITestCase):

#     def setUp(self):
#         self.url = reverse("apply-job")
        
#         # Mock PDF file for uploads
#         self.dummy_resume = SimpleUploadedFile(
#             "resume.pdf",
#             b"PDF content dummy",
#             content_type="application/pdf",
#         )

#     def test_apply_job_success_new_candidate(self):
#         """Test successful application creating a new CandidateProfile, JobApplication, and PublishedEvent."""
#         payload = {
#             "email": "jane@example.com",
#             "full_name": "Jane Doe",
#             "job_id": 101,
#             "skills": "Python, Django, PostgreSQL",
#             "resume": self.dummy_resume,
#         }

#         # MultiPart format is necessary for request.FILES testing
#         response = self.client.post(self.url, payload, format="multipart")

#         # Assert Response Status & Body
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(response.data["message"], "Application submitted successfully")
#         self.assertIn("application", response.data)
#         self.assertIn("status", response.data)

#         # Verify Candidate Profile created
#         candidate = CandidateProfile.objects.get(email="jane@example.com")
#         self.assertEqual(candidate.full_name, "Jane Doe")
#         self.assertEqual(candidate.skills, "Python, Django, PostgreSQL")

#         # Verify Job Application created
#         application = JobApplication.objects.get(id=response.data["application"])
#         self.assertEqual(application.candidate, candidate)
#         self.assertEqual(application.job_id, 101)
        
#         self.assertTrue(application.resume.name.endswith(".pdf"))
#         self.assertIn("resume", application.resume.name)
        
#         # Verify Outbox Event created
#         event = PublishedEvent.objects.get(channel="user_events")
#         self.assertEqual(event.payload["event"], "application_created")
#         self.assertEqual(event.payload["user_application_id"], application.id)
#         self.assertEqual(event.payload["candidate_email"], "jane@example.com")
#         self.assertEqual(event.extra["sender"], "user_service")
#         self.assertEqual(event.extra["receiver"], "admin_service")

#     def test_apply_job_existing_candidate(self):
#         """Test application by an existing candidate (get_or_create behavior)."""
#         existing_candidate = CandidateProfile.objects.create(
#             email="existing@example.com",
#             full_name="John Existing",
#             skills="React",
#         )

#         payload = {
#             "email": "existing@example.com",
#             "full_name": "John Updated Name",  # get_or_create defaults won't overwrite existing full_name
#             "job_id": 102,
#             "resume": self.dummy_resume,
#         }

#         response = self.client.post(self.url, payload, format="multipart")

#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
#         # Verify no duplicate CandidateProfile was created
#         self.assertEqual(CandidateProfile.objects.filter(email="existing@example.com").count(), 1)
        
#         # Verify application linked to the pre-existing candidate
#         application = JobApplication.objects.get(id=response.data["application"])
#         self.assertEqual(application.candidate, existing_candidate)

#     def test_apply_job_missing_required_fields(self):
#         """Test 400 response when mandatory fields are omitted."""
#         invalid_payloads = [
#             {"full_name": "John", "job_id": 1, "resume": self.dummy_resume},  # Missing email
#             {"email": "test@ex.com", "job_id": 1, "resume": self.dummy_resume},  # Missing full_name
#             {"email": "test@ex.com", "full_name": "John", "resume": self.dummy_resume},  # Missing job_id
#             {"email": "test@ex.com", "full_name": "John", "job_id": 1},  # Missing resume file
#         ]

#         for payload in invalid_payloads:
#             response = self.client.post(self.url, payload, format="multipart")
#             self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#             self.assertEqual(response.data["error"], "Missing mandatory fields")

#         # Confirm nothing was committed to DB on failure
#         self.assertEqual(CandidateProfile.objects.count(), 0)
#         self.assertEqual(JobApplication.objects.count(), 0)
#         self.assertEqual(PublishedEvent.objects.count(), 0)
        
