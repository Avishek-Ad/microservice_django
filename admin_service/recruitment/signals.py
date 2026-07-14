from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import AdminApplicationReview, AdminApplicationReviewStatus
import redis
import json

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

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
        
        try:
            redis_client.publish('user_events', json.dumps(payload))
            print(f"[SIGNAL OUT] Sent application update for Application {instance.user_application_id}: {instance.review_status}")
        except redis.RedisError:
            pass