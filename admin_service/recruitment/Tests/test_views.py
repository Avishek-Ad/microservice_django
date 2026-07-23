from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from recruitment.models import JobPosting, AdminApplicationReview, AdminApplicationReviewStatus
from recruitment.serializers import JobPostingSerializer, JobApplicationSerializer

class PublicAdminJobListAPIViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        """
        Create test database records ONCE for all tests in this class
        """
        cls.job_active_1 = JobPosting.objects.create(
            title="Senior Backend Engineer",
            is_active=True
        )
        cls.job_active_2 = JobPosting.objects.create(
            title="Frontend Developer",
            is_active=True
        )

        cls.job_inactive = JobPosting.objects.create(
            title="Deprecated Role",
            is_active=False
        )
        cls.url = reverse('public-admin-job-list')
        
    def test_get_active_jobs_success(self):
        """
        Test fetching active jobs returns 200 ok
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_get_active_jobs_returns_only_active_jobs(self):
        """
        Verify inactive jobs are excluded from payload
        """
        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 2)
        
        response_ids = [data['id'] for data in response.data]
        self.assertNotIn(self.job_inactive.id, response_ids)
    
    def test_get_active_job_ordering(self):
        """
        Verify jobs are ordered in descending order (newest first)
        """
        response = self.client.get(self.url)
        
        self.assertEqual(self.job_active_2.id, response.data[0]['id'])
        self.assertEqual(self.job_active_1.id, response.data[1]['id'])
        
    def test_get_active_job_matching_serializer_output(self):
        """
        Verifying response data matches the serializer's output directly
        """
        job_posting = JobPosting.objects.filter(is_active=True).order_by('-created_at')
        serializer = JobPostingSerializer(job_posting, many=True)
        
        response = self.client.get(self.url)
        self.assertEqual(response.data, serializer.data)
        
    def test_get_active_jobs_empty_list(self):
        """Verify an empty array is returned when no active jobs exist."""
        JobPosting.objects.filter(is_active=True).update(is_active=False)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])  
        
class JobListCreateAPIViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.job_1 = JobPosting.objects.create(
            title="Senior Backend Engineer",
            is_active=True
        )
        cls.job_2 = JobPosting.objects.create(
            title="Frontend Developer",
            is_active=False
        )
        cls.url = reverse('job-list-create')
        
    def test_list_jobs_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
    def test_job_list_returns_all_jobs(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 2)
        
    def test_list_jobs_matches_serializer_data(self):
        job_postings = JobPosting.objects.all()
        serializer = JobPostingSerializer(job_postings, many=True)
        
        response = self.client.get(self.url)
        self.assertEqual(serializer.data, response.data)
        
    def test_create_job_success(self):
        new_job_post_payload = {
            "title": "Devops Engineer",
            "department": "software developer",
            "description": "Devops Engineer job description"
        }
        
        initial_count = JobPosting.objects.count()
        
        response = self.client.post(self.url, data=new_job_post_payload, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JobPosting.objects.count(), initial_count+1)
        
        new_job_posting = JobPosting.objects.get(id=response.data["id"])
        self.assertEqual(new_job_posting.title, new_job_post_payload["title"])
        
    def test_create_job_invalid_payload(self):
        new_job_post_invalid_payload = {
            "department": "software developer",
            "description": "Devops Engineer job description"
        }
        response = self.client.post(self.url, data=new_job_post_invalid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)
        
class JobRetriveUpdateDestroyAPIViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.job = JobPosting.objects.create(
            title="Full Stack Engineer",
            description="Python & React experience required",
            is_active=True
        )
        
        cls.url = reverse('job-detail', kwargs={'pk': cls.job.id})
        cls.invalid_url = reverse('job-detail', kwargs={'pk': 99999})
        
    def test_retrive_job_success(self):
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.job.pk)
        self.assertEqual(response.data['title'], self.job.title)
        
    def test_retrive_job_job_found(self):
        response = self.client.get(self.invalid_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_full_update_job_success(self):
        payload = {
            "title": "Lead Software Engineer",
            "description": "Updated description",
            "department": "software development",
            "is_active": False
        }
        response = self.client.put(self.url, data=payload, format="json")        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # refresh object state form db to verify presistance
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, payload['title'])
        self.assertFalse(self.job.is_active)
    
    def test_partial_update_job_success(self):
        payload = {"title": "Principal Architect"}
        
        response = self.client.patch(self.url, data=payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Title updated, but description remains unchanged
        self.job.refresh_from_db()
        self.assertEqual(self.job.title, "Principal Architect")
        self.assertEqual(self.job.description, "Python & React experience required")
        
    def test_update_job_invalid_data(self):
        payload = {"title": ""}
        
        response = self.client.put(self.url, data=payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        
    def test_delete_job_success(self):
        initial_count = JobPosting.objects.count()
        
        response = self.client.delete(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(JobPosting.objects.count(), initial_count - 1)
        self.assertFalse(JobPosting.objects.filter(pk=self.job.pk).exists())

    def test_delete_job_not_found(self):
        response = self.client.delete(self.invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class JobApplicationsListAPIViewTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Job posting WITH applications
        cls.job = JobPosting.objects.create(
            title="Senior Python Engineer",
            is_active=True
        )
        
        # Create two applications for this job
        cls.app_1 = AdminApplicationReview.objects.create(
            user_application_id=1,
            job=cls.job,
            candidate_name="Alice Smith",
            candidate_email="alice@example.com"
        )
        cls.app_2 = AdminApplicationReview.objects.create(
            user_application_id=1,
            job=cls.job,
            candidate_name="Bob Jones",
            candidate_email="bob@example.com"
        )

        # Job posting WITHOUT applications
        cls.empty_job = JobPosting.objects.create(
            title="DevOps Lead",
            is_active=True
        )

        cls.url = reverse('job-applications-list', kwargs={'job_id': cls.job.id})
        cls.empty_job_url = reverse('job-applications-list', kwargs={'job_id': cls.empty_job.id})
        cls.invalid_url = reverse('job-applications-list', kwargs={'job_id': 99999})
    
    def test_get_job_applications_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_job_applications_returns_correct_count(self):
        response = self.client.get(self.url)
        
        self.assertEqual(len(response.data), 2)
                
        returned_ids = [app['id'] for app in response.data]
        self.assertIn(self.app_1.id, returned_ids)
        self.assertIn(self.app_2.id, returned_ids)

    def test_get_job_applications_matches_serializer_data(self):
        applications = self.job.applications.all()
        serializer = JobApplicationSerializer(applications, many=True)

        response = self.client.get(self.url)
        self.assertEqual(response.data, serializer.data)

    def test_get_job_applications_empty_list(self):
        response = self.client.get(self.empty_job_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])
        
    def test_get_job_applications_invalid_job_id_returns_404(self):
        response = self.client.get(self.invalid_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_job_applications_404_custom_message(self):
        non_existent_id = 99999
        response = self.client.get(self.invalid_url)
        
        expected_message = f"Job posting with id {non_existent_id} not found"
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], expected_message)
        
class JobApplicationsStatusChangeTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        """Create test database state ONCE for all tests in this class."""
        cls.job = JobPosting.objects.create(
            title="Backend Lead",
            is_active=True
        )
        cls.application = AdminApplicationReview.objects.create(
            job=cls.job,
            user_application_id=1,
            review_status=AdminApplicationReviewStatus.UNDER_REVIEW,
            candidate_name="Bob Jones",
            candidate_email="bob@example.com"
        )

        # Another job to test cross-posting isolation
        cls.other_job = JobPosting.objects.create(
            title="Frontend Dev",
            is_active=True
        )

        # URL for valid job and application
        cls.url = reverse(
            'job-status-change', 
            kwargs={'job_id': cls.job.id, 'user_app_id': cls.application.user_application_id}
        )
    
    def test_change_status_to_hired_success(self):
        payload = {"new_status": "hired"}
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify response message contract
        expected_msg = f"{self.application.user_application_id} is hired for job id {self.job.id}"
        self.assertEqual(response.data["message"], expected_msg)

        # Refresh database state
        self.application.refresh_from_db()
        self.assertEqual(self.application.review_status, AdminApplicationReviewStatus.HIRED)

    def test_change_status_to_rejected_success(self):
        payload = {"new_status": "rejected"}
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.application.refresh_from_db()
        self.assertEqual(self.application.review_status, AdminApplicationReviewStatus.REJECTED)

    def test_change_status_to_under_review_success(self):
        payload = {"new_status": "under_review"}
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.application.refresh_from_db()
        self.assertEqual(self.application.review_status, AdminApplicationReviewStatus.UNDER_REVIEW)
    
    def test_change_status_invalid_choice_returns_400(self):
        payload = {"new_status": "promoted_to_ceo"}  # Not in allowed choices
        response = self.client.post(self.url, data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["message"], 
            "the given status was not among accepted status"
        )

    def test_change_status_missing_payload_returns_400(self):
        response = self.client.post(self.url, data={}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["message"], 
            "the given status was not among accepted status"
        )
    
    def test_change_status_invalid_job_id_returns_404(self):
        url = reverse(
            'job-status-change', 
            kwargs={'job_id': 99999, 'user_app_id': self.application.user_application_id}
        )
        response = self.client.post(url, data={"new_status": "hired"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_change_status_invalid_user_app_id_returns_404(self):
        url = reverse(
            'job-status-change', 
            kwargs={'job_id': self.job.id, 'user_app_id': 99999}
        )
        response = self.client.post(url, data={"new_status": "hired"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_change_status_application_belongs_to_different_job_returns_404(self):
        url = reverse(
            'job-status-change', 
            kwargs={'job_id': self.other_job.id, 'user_app_id': self.application.user_application_id}
        )
        response = self.client.post(url, data={"new_status": "hired"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
