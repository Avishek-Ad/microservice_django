from django.core.management.base import BaseCommand
from logs.models import SystemLog
from django.conf import settings
from confluent_kafka import Consumer, KafkaError, KafkaException
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
            'group.id': 'django-service-consumer-group',
            'auto.offset.reset': 'earliest',          
            'enable.auto.commit': False,    # Disable auto-commit for manual acknowledgment
            'session.timeout.ms': 45000,    # Detect worker crashes within 45s
        }
        
        consumer = Consumer(conf)
        
        # subscribe to topic
        topics = ['admin_events', 'user_events', 'audit_events']
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
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # end of partitioned events
                        self.stdout.write(f"Reached end of partition: {msg.topic()} [{msg.partition()}]")
                    else:
                        raise KafkaException(msg.error())
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
        try:
            key = msg.key().decode('utf-8') if msg.key() else None
            value = msg.value().decode('utf-8') if msg.value() else None
            
            self.stdout.write(f"Received message from topic {msg.topic()} [{msg.partition()}]: Key={key}")
            
            if value:
                payload = json.loads(value)
                 
                # call functions based on payload['event']
                if payload['event'] in ["application_created", "application_status_update"]:
                    self.handle_application_created_event(payload)
                else:
                    self.stdout.write(self.style.WARNING(f"Unknown Event Arrived {payload['event']}"))
                    
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error processing message: {e}"))
    
    def handle_shutdown(self, signum, frame):
        """
        Catches termination signals to break out of the while loop cleanly.
        """
        self.stdout.write(self.style.WARNING(f"\nSignal {signum} received. Initiating graceful shutdown..."))
        self.shutdown_requested = True
        
    def handle_application_created_event(self, payload):
        extra_fields = payload['extra']
        
        log_type = extra_fields.get('log_type')
        sender = extra_fields.get('sender')
        receiver = extra_fields.get('receiver')
        event_type = extra_fields.get('event_type')
        occured_at = extra_fields.get('occured_at')
        
        # TODO: use nosql database 