from celery import shared_task

@shared_task
def publishing_events_to_kafka():
    pass