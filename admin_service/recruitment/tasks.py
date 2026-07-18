from celery import shared_task
from .models import PublishedEvent
from .kafka_client import get_kafka_producer, delivery_report
import json

@shared_task
def publishing_events_in_db_to_kafka():
    producer = get_kafka_producer()
    
    publishedEvents = PublishedEvent.objects.filter(is_consumed=False)[:50]
        
    if not publishedEvents.exists():
        return "No New Events found"
            
    success_count = 0
            
    for publishedEvent in publishedEvents:
        try:
            payload = {
                **publishedEvent.payload,
                "extra": publishedEvent.extra
            }
                
            value_bytes = json.dumps(payload).encode('utf-8')
            key_bytes = str(publishedEvent.id).encode('utf-8')
                    
            producer.produce(
                topic=publishedEvent.channel,
                key=key_bytes,
                value=value_bytes,
                callback=delivery_report
            )
            
            # Force network flush right here to get confirmation for *this* message
            unflushed_count = producer.flush(timeout=2.0)
            
            if unflushed_count > 0:
                print(f"Failed to flush message to Kafka for event {publishedEvent.id}. Skipping DB update.")
                continue
         
            # Update individually only after successful flush confirmation
            publishedEvent.is_consumed = True
            publishedEvent.save()
            success_count += 1
                    
        except Exception as e:
            print(f"Failed to queue event {publishedEvent.id}: {str(e)}")
            
        # Triggers the background delivery_report callback engine 
        producer.poll(0)
            
    return f"Successfully Published {success_count} events one-by-line"