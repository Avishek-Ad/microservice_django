from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import candidateProfile, JobApplication
from django.conf import settings
from .models import PublishedEvent
from django.db import transaction
from datetime import datetime, timezone
from opensearch_client import get_opensearch_client
import requests

class JobSearchAPIView(APIView):
    def get(self, request):
        query_string = request.query_params.get('q', '')
        department = request.query_params.get('department', None)
        
        # building opensearch query
        # search only among active jobs
        must_clause = [
            {"term": {"is_active": True}}
        ]
        
        # multi match text search across title and description
        if query_string:
            must_clause.append({
                "multi_match": {
                    "query": query_string,
                    "fields": ["title^2", "description"], # title has double refrence weight
                    "fuzziness": "AUTO" # handles typo
                }
            })
        
        if department:
            must_clause.append({"term": {"department": department}})
        
        search_body = {
            "query":  {
                "bool": {
                    "must": must_clause
                }
            },
            "size": 10
        }
        
        try:
            client = get_opensearch_client()
            response = client.search(index="jobs", body=search_body)
            
            hits = response['hits']['hits']
            results = []
            for hit in hits:
                job_item = hit['_source']
                job_item['_score'] = hit['_score'] # search relevence score
                results.append(job_item)
                
            return Response({'results': results}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class JobListAPIView(APIView):
    def get(self, request):
        try:
            admin_url = f"{settings.ADMIN_MICROSERVICE_URL}/api/posted_jobs/"
            response = requests.get(admin_url, timeout=5)
            print(response)
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
        
        with transaction.atomic():
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
            # for logging
            extra = {
                "log_type": "EVENT",
                "sender": "user_service",
                "receiver": "admin_service", # intended receiver
                "event_type": "application_created",
                "occured_at": datetime.now(timezone.utc).isoformat()
            }
            PublishedEvent.objects.create(
                channel='admin_events',
                payload=payload,
                extra=extra
            )
        
        return Response({
            "message": "Application submitted successfully",
            "application": application.id,
            "status": application.status,
        }, status=status.HTTP_201_CREATED)
            
        