from django.core.management.base import BaseCommand
from recruitment.models import JobPosting, AdminApplicationReview
from django.conf import settings
import redis
import json

class Command(BaseCommand):
    help = "Running a contineous worker process listening for asynchronous application submission from redis"
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Initializing redis application listening connection..."))
        
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        pubsub = r.pubsub()
        
        pubsub.subscribe("admin_events")
        
        self.stdout.write(self.style.SUCCESS("Successfully listening to admin_events channel ..."))
        
        # contineous listening loop
        for message in pubsub.listen():
            if message['type'] != "message":
                continue
            
            try:
                data = json.loads(message['data'].decode('utf8'))
                
                if data.get('event') == 'application_created':
                    user_application_id = data.get('user_application_id')
                    name = data.get('candidate_name')
                    email = data.get('candidate_email')
                    job_id = data.get('job_id')
                    
                    try:
                        job_posting = JobPosting.objects.get(id=job_id)
                        
                        # creating review record
                        AdminApplicationReview.objects.create(
                            user_application_id=user_application_id,
                            candidate_name=name,
                            candidate_email=email,
                            job=job_posting
                        )
                        
                        self.stdout.write(self.style.SUCCESS(f"[ALERT] Application {user_application_id} successfully mapped to Admin DB review dashboard!"))
                        
                    except JobPosting.DoesNotExist:
                        self.stdout(self.style.WARNING(f"[ERROR] Received job posting for non existing job_id: {job_id}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error parsing redis payload packet: {str(e)}"))