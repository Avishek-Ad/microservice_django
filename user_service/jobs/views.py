from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import candidateProfile, JobApplication
from django.conf import settings
import requests
import redis
import json

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

class JobListAPIView(APIView):
    def get(self, request):
        try:
            admin_url = "http://localhost:8001/api/jobs"
            response = requests.get(admin_url, timeout=5)
            if response.status_code == status.HTTP_200_OK:
                return Response(response.json(), status=response.status_code)
            return Response({"error": "Admin service failed to provide data"}, status=response.status_code)
        except requests.exceptions.RequestException:
            return Response({"error": "Admin microservice is currently unreachable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
    
class ApplyJobAPIView(APIView):
    def post(self, request):
        email = request.data.get("email")
        full_name = request.data.get("full_name")
        job_id = request.data.get("job_id")
        skills = request.data.get("skills")
        
        if not email or not full_name or not job_id:
            return Response({'error': "Missing mandatory fields"}, status=status.HTTP_400_BAD_REQUEST)
        
        # getting or creating candidate record
        candidate, _ = candidateProfile.objects.get_or_create(
            email=email,
            defaults={
                'full_name': full_name,
                'skills': skills
            }
        )
        
        application = JobApplication.objects.create(candidate=candidate, job_id=job_id)
        
        payload = {
            "event": "application_created",
            "user_application_id": application.id,
            "candidate_name": candidate.full_name,
            "candidate_email": candidate.email,
            "job_id": job_id
        }
        
        try:
            redis_client.publish('hr_event', json.dumps(payload)) # channel is hr_event and message is payload
        except redis.RedisError:
            
            pass # silent fail
        
        return Response({
            "message": "Application submitted successfully",
            "application": application.id,
            "status": application.status,
        }, status=status.HTTP_201_CREATED)
            
        