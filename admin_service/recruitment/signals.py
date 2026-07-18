from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import AdminApplicationReview, AdminApplicationReviewStatus, PublishedEvent, JobPosting
from datetime import datetime, timezone

@receiver(post_save, sender=AdminApplicationReview)
def publish_application_status_to_user_service(sender, instance, created, **kwargs):
    """
    Fires whenever AdminApplicationReview object changes
    This is used to send aspplication status to user service when status changes form "NEW" or "UNDER_REVIEW"
    """
    if created:
        return
    
    if instance.review_status in [AdminApplicationReviewStatus.HIRED, AdminApplicationReviewStatus.REJECTED]:
        payload = {
            "event": "application_status_update",
            "user_application_id": instance.user_application_id,
            "new_status": instance.review_status
        }
        
        extra = {
            "log_type": "EVENT",
            "sender": "admin_service",
            "receiver": "user_service", # intended receiver
            "event_type": "application_status_update",
            "occured_at": datetime.now(timezone.utc).isoformat()
        }
        PublishedEvent.objects.create(
            channel='admin_events',
            payload=payload,
            extra=extra
        )
        
@receiver(post_save, sender=JobPosting)
def send_job_for_indexing(sender, instance, created, **kwargs):
    payload = {
            "job_id": instance.id,
            "title": instance.title,
            "description": instance.description,
            "department": instance.department,
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat() if instance.created_at else None
        }
    extra = {
            "log_type": "EVENT",
            "sender": "admin_service",
            "receiver": "user_service", # intended receiver
            "occured_at": datetime.now(timezone.utc).isoformat()
        }
    
    if created:
        payload["event"] = "job_created"
        extra["event_type"] = "job_created"
    else:
        payload["event"] = "job_updated"
        extra["event_type"] = "job_updated"
    
    PublishedEvent.objects.create(
        channel='admin_events',
        payload=payload,
        extra=extra
    )

@receiver(post_delete, sender=JobPosting)
def send_delete_event_for_job(sender, instance, **kwargs):
    payload = {
        "event": "job_deleted",
        "job_id": instance.id,
        }
    extra = {
        "log_type": "EVENT",
        "sender": "admin_service",
        "receiver": "user_service", # intended receiver
        "event_type": "job_deleted",
        "occured_at": datetime.now(timezone.utc).isoformat()
    }
    PublishedEvent.objects.create(
        channel='admin_events',
        payload=payload,
        extra=extra
    )