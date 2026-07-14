from django.core.management.base import BaseCommand
from jobs.models import JobApplication, JobApplicationStatus
from django.conf import settings
import redis
import json

class Command(BaseCommand):
    help = "Running a contineous worker process listening for asynchronous application submission from redis"
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Initializing redis application listening connection..."))
        
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        pubsub = r.pubsub()
        
        pubsub.subscribe("user_events")
        
        self.stdout.write(self.style.SUCCESS("Successfully listening to user_events channel ..."))
        
        # contineous listening loop
        for message in pubsub.listen():
            if message['type'] != "message":
                continue
            
            try:
                data = json.loads(message['data'].decode('utf8'))
                
                if data.get('event') == 'application_status_update':
                    user_application_id = data.get('user_application_id')
                    new_status = data.get('new_status')
                    
                    try:
                        job_application = JobApplication.objects.get(id=user_application_id)
                        
                        # updating status of job application
                        if new_status == "hired":
                            job_application.status = JobApplicationStatus.APPROVED
                        elif new_status == "rejected":
                            job_application.status = JobApplicationStatus.REJECTED
                            
                        job_application.save()
                        
                        self.stdout.write(self.style.SUCCESS(f"[ALERT] Job Application {user_application_id} status successfully changed to reflect admin's review!"))
                        
                    except JobApplication.DoesNotExist:
                        self.stdout(self.style.WARNING(f"[ERROR] Received job application for non existing user_application_id: {user_application_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error parsing redis payload packet: {str(e)}"))