from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AdminApplicationReview, AdminApplicationReviewStatus, PublishedEvent
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
            "event_type": "application_created",
            "occured_at": datetime.now(timezone.utc()).isoformat()
        }
        PublishedEvent.objects.create(
            channel='user_events',
            payload=payload,
            extra=extra
        )