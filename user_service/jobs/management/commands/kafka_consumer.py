from django.core.management.base import BaseCommand
from jobs.models import JobApplication, JobApplicationStatus, ProcessedEvent
from django.conf import settings
from confluent_kafka import Consumer, KafkaError, KafkaException
from opensearch_client import get_opensearch_client
import signal # for stopping loop without data loss
import json

class Command(BaseCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.shutdown_requested = False
        
    def handle(self, *args, **kwargs):
        # signal handler for gracefull shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown) # SIGINT is triggered when we press ctrl+c ourself
        signal.signal(signal.SIGTERM, self.handle_shutdown) # SIGTERM is triggered when docker or kuberneties stops this process
        
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVER,
            'group.id': 'user-service-consumer-group',
            'auto.offset.reset': 'earliest',          
            'enable.auto.commit': False,    # Disable auto-commit for manual acknowledgment
            'session.timeout.ms': 45000,    # Detect worker crashes within 45s
            'allow.auto.create.topics': True,
        }
        
        consumer = Consumer(conf)
        
        # subscribe to topic
        topics = ['admin_events']
        self.stdout.write(self.style.SUCCESS(f"Subscribing to topics: {topics}"))
        consumer.subscribe(topics)

        self.stdout.write(self.style.SUCCESS("Kafka consumer started. Listening for messages..."))
        
        try:
            while not self.shutdown_requested:
                # poll for a single message
                msg = consumer.poll(timeout=1.0) # in second
                
                if msg is None:
                    continue
                
                if msg.error():
                    error_code = msg.error().code()
                    
                    if error_code == KafkaError._PARTITION_EOF:
                        self.stdout.write(f"Reached end of partition: {msg.topic()} [{msg.partition()}]")
                    elif error_code == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        self.stdout.write(self.style.WARNING(
                            f"Topic {msg.topic()} not available yet. Retrying..."
                        ))
                    else:
                        # 🚀 CHANGE HERE: Log the error instead of raising an exception!
                        # This keeps the loop running even if Kafka hiccups temporarily.
                        self.stderr.write(self.style.ERROR(f"Kafka notice/error: {msg.error()}"))
                else:
                    # a valid message
                    self.process_message(msg, consumer)
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Fatal consumer error: {e}"))
        finally:
            # clean up, close connection and shutdown
            self.stdout.write(self.style.WARNING("Closing Kafka consumer..."))
            consumer.close()
            self.stdout.write(self.style.SUCCESS("Kafka consumer closed gracefully."))
            
    def process_message(self, msg, consumer):
        created_tracking_event = False
        event_id = None
        try:
            key = msg.key().decode('utf-8') if msg.key() else None
            value = msg.value().decode('utf-8') if msg.value() else None
            
            self.stdout.write(f"Received message from topic {msg.topic()} [{msg.partition()}]: Key={key}")
            
            if value:
                payload = json.loads(value)
                
                # ensure idempotenty
                event_id = payload.get("event_id")
        
                _, created = ProcessedEvent.objects.get_or_create(event_id=event_id)
                
                if not created:
                    self.stdout.write(self.style.WARNING(f"Event {event_id} already processed. Skipping safely."))
                    consumer.commit(msg, asynchronous=False)
                    return

                created_tracking_event = True
                                 
                # call functions based on payload['event']
                if payload['event'] == "application_status_update":
                    self.handle_application_status_update(payload)
                elif payload['event'] in ["job_created", "job_updated"]:
                    self.handle_index_or_update_document(payload)
                elif payload['event'] == "job_deleted":
                    self.handle_delete_document(payload)
                else:
                    self.stdout.write(self.style.WARNING(f"Unknown Event Arrived {payload['event']}"))
            # commit offset anually after successful processing
            consumer.commit(msg, asynchronous=False)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing message: {e}"))
            # roll back the tracking
            if created_tracking_event and event_id:
                self.stdout.write(self.style.WARNING(f"Rolling back tracking for event {event_id} to allow retries."))
                ProcessedEvent.objects.filter(event_id=event_id).delete()
    
    def handle_shutdown(self, signum, frame):
        self.stdout.write(self.style.WARNING(f"\nSignal {signum} received. Initiating graceful shutdown..."))
        self.shutdown_requested = True
        
    def handle_application_status_update(self, payload):
        
        user_application_id = payload['user_application_id']
        new_status = payload['new_status']
        
        try:
            job_application = JobApplication.objects.get(id=user_application_id)
            
            if new_status == "hired":
                job_application.status = JobApplicationStatus.APPROVED
            elif new_status == "rejected":
                job_application.status = JobApplicationStatus.REJECTED
            
            job_application.save()    
            
            self.stdout.write(self.style.SUCCESS(f"[ALERT] Job Application {user_application_id} status successfully changed to reflect admin's review!"))
        except JobApplication.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"[ERROR] Received job application for non existing user_application_id: {user_application_id}"))
            
    def handle_index_or_update_document(self, payload):
        os_client = get_opensearch_client()
        job_id = str(payload.get("job_id"))
        document_body={
            "id": payload.get("job_id"),
            "title": payload.get("title"),
            "description": payload.get("description"),
            "department": payload.get("department"),
            "is_active": payload.get("is_active"),
            "created_at": payload.get("created_at")
        }
        os_client.index(
            index="jobs",
            id=job_id,
            body=document_body,
            refresh=True
        )
        self.stdout.write(f"Synced job {job_id} to OpenSearch.")
    
    def handle_delete_document(self, payload):
        os_client = get_opensearch_client()
        job_id = str(payload.get("job_id"))
        if os_client.exists(index="jobs", id=job_id):
            os_client.delete(index="jobs", id=job_id)
            self.stdout.write(f"Deleted job {job_id} from OpenSearch.")