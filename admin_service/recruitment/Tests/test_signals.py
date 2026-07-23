import uuid
from django.test import TestCase
from recruitment.models import (
    JobPosting, 
    AdminApplicationReview, 
    AdminApplicationReviewStatus, 
    PublishedEvent
)


class PublishApplicationStatusSignalTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.job = JobPosting.objects.create(
            title="Backend Lead",
            is_active=True
        )

    def test_signal_publishes_event_when_status_changed_to_hired(self):
        application = AdminApplicationReview.objects.create(
            job=self.job,
            user_application_id=101,
            review_status=AdminApplicationReviewStatus.NEW,
            candidate_name="Ram Yadav",
            candidate_email="ram@gmail.com"
        )

        # Verify no application status update event exists yet for this user_application_id
        self.assertFalse(
            PublishedEvent.objects.filter(
                payload__event="application_status_update",
                payload__user_application_id=101
            ).exists()
        )

        # Update status to HIRED
        application.review_status = AdminApplicationReviewStatus.HIRED
        application.save()

        # Retrieve the EXACT event created for this user_application_id
        event = PublishedEvent.objects.get(
            payload__event="application_status_update",
            payload__user_application_id=application.user_application_id
        )

        # Assertions on the specific event
        self.assertEqual(event.channel, 'admin_events')
        self.assertEqual(event.payload['new_status'], AdminApplicationReviewStatus.HIRED)

        # Validate UUID format
        uuid.UUID(event.payload['event_id'])

        # Validate extra metadata
        self.assertEqual(event.extra['sender'], 'admin_service')
        self.assertEqual(event.extra['receiver'], 'user_service')
        self.assertEqual(event.extra['event_type'], 'application_status_update')
        self.assertIn('occured_at', event.extra)
    
    def test_signal_publishes_event_when_status_changed_to_rejected(self):
        application = AdminApplicationReview.objects.create(
            job=self.job,
            user_application_id=102,
            review_status=AdminApplicationReviewStatus.UNDER_REVIEW,
            candidate_name="Sita Sharma",
            candidate_email="sita@gmail.com"
        )

        application.review_status = AdminApplicationReviewStatus.REJECTED
        application.save()

        # Target the specific event created for this user application
        event = PublishedEvent.objects.get(
            payload__event="application_status_update",
            payload__user_application_id=application.user_application_id
        )
        self.assertEqual(event.payload['new_status'], AdminApplicationReviewStatus.REJECTED)
        
    def test_signal_does_not_fire_on_instance_creation(self):
        application = AdminApplicationReview.objects.create(
            job=self.job,
            user_application_id=103,
            review_status=AdminApplicationReviewStatus.HIRED,  # Even if status is HIRED on creation
            candidate_name="Hari Sharma",
            candidate_email="hari@gmail.com"
        )

        # Check that NO status update event was published for this application ID
        status_update_exists = PublishedEvent.objects.filter(
            payload__event="application_status_update",
            payload__user_application_id=application.user_application_id
        ).exists()
        
        self.assertFalse(status_update_exists)

    def test_signal_does_not_fire_for_other_statuses(self):
        application = AdminApplicationReview.objects.create(
            job=self.job,
            user_application_id=104,
            review_status=AdminApplicationReviewStatus.NEW,
            candidate_name="Hari Puri",
            candidate_email="hari@gmail.com"
        )

        # Update to UNDER_REVIEW
        application.review_status = AdminApplicationReviewStatus.UNDER_REVIEW
        application.save()

        # Check that NO status update event was published for this application ID
        status_update_exists = PublishedEvent.objects.filter(
            payload__event="application_status_update",
            payload__user_application_id=application.user_application_id
        ).exists()

        self.assertFalse(status_update_exists)


class SendJobForIndexingSignalTest(TestCase):
    def test_signal_publishes_event_on_job_creation(self):        
        job = JobPosting.objects.create(
            title="Senior Python Developer",
            description="We are looking for a Python dev...",
            department="Engineering",
            is_active=True
        )

        # Retrieve the specific event created for this job ID
        event = PublishedEvent.objects.get(
            payload__event="job_created",
            payload__job_id=job.id
        )

        # Validate Channel
        self.assertEqual(event.channel, 'admin_events')

        # Validate Payload structure
        self.assertEqual(event.payload['event'], 'job_created')
        self.assertEqual(event.payload['job_id'], job.id)
        self.assertEqual(event.payload['title'], "Senior Python Developer")
        self.assertEqual(event.payload['description'], "We are looking for a Python dev...")
        self.assertEqual(event.payload['department'], "Engineering")
        self.assertTrue(event.payload['is_active'])
        self.assertIsNotNone(event.payload['created_at'])

        # Validate event_id is a valid UUID
        uuid.UUID(event.payload['event_id'])

        # Validate Extra metadata fields
        self.assertEqual(event.extra['log_type'], 'EVENT')
        self.assertEqual(event.extra['sender'], 'admin_service')
        self.assertEqual(event.extra['receiver'], 'user_service')
        self.assertEqual(event.extra['event_type'], 'job_created')
        self.assertIn('occured_at', event.extra)

    def test_signal_publishes_event_on_job_update(self):        
        # Create the job
        job = JobPosting.objects.create(
            title="Junior QA Engineer",
            description="Manual testing role",
            department="QA",
            is_active=True
        )

        # Update the job
        job.title = "Lead QA Engineer"
        job.is_active = False
        job.save()

        # Assert the 'job_updated' event exists
        event = PublishedEvent.objects.get(
            payload__event="job_updated",
            payload__job_id=job.id
        )

        # Validate Payload fields reflect the NEW values
        self.assertEqual(event.payload['event'], 'job_updated')
        self.assertEqual(event.payload['title'], "Lead QA Engineer")
        self.assertFalse(event.payload['is_active'])

        # Validate Extra metadata event_type
        self.assertEqual(event.extra['event_type'], 'job_updated')

    def test_job_lifecycle_creates_created_and_updated_events(self):        
        job = JobPosting.objects.create(
            title="DevOps Specialist",
            is_active=True
        )

        job.title = "Site Reliability Engineer (SRE)"
        job.save()

        # Query all events generated for this specific job
        job_events = PublishedEvent.objects.filter(payload__job_id=job.id)

        self.assertEqual(job_events.count(), 2)
        
        event_types = set(job_events.values_list('payload__event', flat=True))
        self.assertEqual(event_types, {'job_created', 'job_updated'})
        

class SendDeleteEventForJobSignalTest(TestCase):
    def test_signal_publishes_event_on_job_deletion(self):        
        # Create a job (this will fire post_save signal -> job_created event)
        job = JobPosting.objects.create(
            title="Frontend Developer",
            description="React/Vue specialist",
            department="Engineering",
            is_active=True
        )
        job_id = job.id  # Save ID before deleting

        # Verify no job_deleted event exists yet
        self.assertFalse(
            PublishedEvent.objects.filter(
                payload__event="job_deleted",
                payload__job_id=job_id
            ).exists()
        )

        # Delete the job posting (triggers post_delete signal)
        job.delete()

        # Retrieve the specific job_deleted event
        event = PublishedEvent.objects.get(
            payload__event="job_deleted",
            payload__job_id=job_id
        )

        # Validate Channel
        self.assertEqual(event.channel, 'admin_events')

        # Validate Payload
        self.assertEqual(event.payload['event'], 'job_deleted')
        self.assertEqual(event.payload['job_id'], job_id)
        
        # Validate event_id is a valid UUID
        uuid.UUID(event.payload['event_id'])

        # Validate Extra metadata
        self.assertEqual(event.extra['log_type'], 'EVENT')
        self.assertEqual(event.extra['sender'], 'admin_service')
        self.assertEqual(event.extra['receiver'], 'user_service')
        self.assertEqual(event.extra['event_type'], 'job_deleted')
        self.assertIn('occured_at', event.extra)

    def test_job_full_lifecycle_events(self):        
        job = JobPosting.objects.create(title="Temporary Role")
        job_id = job.id

        job.delete()

        # Fetch all events associated with this job_id
        events = PublishedEvent.objects.filter(payload__job_id=job_id)
        
        self.assertEqual(events.count(), 2)
        event_types = set(events.values_list('payload__event', flat=True))
        self.assertEqual(event_types, {'job_created', 'job_deleted'})