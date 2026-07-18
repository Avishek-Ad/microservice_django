from celery import shared_task
from .models import PublishedEvent
from .kafka_client import get_kafka_producer, delivery_report
from django.db import transaction
import json

@shared_task
def publishing_events_in_db_to_kafka():
    producer = get_kafka_producer()
    
    with transaction.atomic():
        publishedEvents = list(PublishedEvent.objects.filter(is_consumed=False).select_for_update(skip_locked=True))
        # select_for_update() prevents other concurrent tasks from picking up the same records
    
    if publishedEvents is None:
        return "No New Events found"
        
    successfully_published_ids = []
        
    for publishedEvent in publishedEvents:
        try:
            payload = {
                **publishedEvent.payload,
                "extra":publishedEvent.extra
            }
            
            value_bytes = json.dumps(payload).encode('utf-8')
            key_bytes = str(publishedEvent.id).encode('utf-8') # for ordering
                
            producer.produce(
            topic="admin_events",
            key=key_bytes,
            value=value_bytes,
            callback=delivery_report
        )
                
            publishedEvent.is_consumed = True
            successfully_published_ids.append(publishedEvent.id)
                
        except Exception as e:
            print(f"Failed to queue events {publishedEvent.id}: {str(e)}")
        
    producer.poll(0) # server local back and send outstanding cllback
        
    # will give if count of the number messages that fails
    unflushed_count = producer.flush(timeout=10.0)
        
    if unflushed_count > 0:
        raise RuntimeError(f"Failed to flush {unflushed_count} messages to Kafka. Rolling back transaction.")
        
    if successfully_published_ids:
        with transaction.atomic():
            PublishedEvent.objects.bulk_update(successfully_published_ids, fields=['is_consumed'])
    
    return f"successfully Published {len(publishedEvents)} vents"
        
            