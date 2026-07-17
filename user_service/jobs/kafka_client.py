from confluent_kafka import Producer

_producer = None

def delivery_report(err, msg):
    if err is None:
        print("[SUCCESS] Event Published to kafka successfully")
    else:
        print(f"[FAILURE] Event publish failed to {msg.topic()} [{msg.partition()}]")
        
def get_kafka_producer():
    global _producer
    if _producer is None:
        config = {
            'bootstrap.servers':'localhost:9092', # later use env from docker compose internal url
            'client.id':'user-service-producer'
        }
        _producer = Producer(config)
    return _producer