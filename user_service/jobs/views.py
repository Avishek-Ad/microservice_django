from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import candidateProfile, JobApplication
from django.conf import settings
from .models import PublishedEvent
from django.db import transaction
from datetime import datetime, timezone
from opensearch_client import get_opensearch_client
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer
from rest_framework import serializers
import requests
import uuid

class JobSearchAPIView(APIView):
    @extend_schema(
        summary="Search active job postings",
        description="Queries OpenSearch for active job postings using full-text search and department filters.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search query string matched against title and description (supports fuzzy search)",
                required=False
            ),
            OpenApiParameter(
                name="department",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter jobs by specific department name",
                required=False
            ),
        ],
        responses={
            200: inline_serializer(
                name="JobSearchResultResponse",
                fields={
                    "results": serializers.ListField(
                        child=inline_serializer(
                            name="OpenSearchJobHit",
                            fields={
                                "id": serializers.IntegerField(),
                                "title": serializers.CharField(),
                                "department": serializers.CharField(),
                                "description": serializers.CharField(),
                                "is_active": serializers.BooleanField(),
                                "_score": serializers.FloatField(help_text="Search relevance score from OpenSearch"),
                            }
                        )
                    )
                }
            ),
            500: inline_serializer('OpenSearchError', fields={'error': serializers.CharField()}),
        }
    )
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
    @extend_schema(
        summary="Proxy list all posted jobs from Admin Microservice",
        description="Fetches live posted jobs by calling the admin service internal REST endpoint.",
        responses={
            200: inline_serializer('AdminJobListResponse', fields={'results': serializers.ListField(child=serializers.DictField())}),
            500: inline_serializer('AdminServiceError', fields={'error': serializers.CharField()}),
            503: inline_serializer('AdminServiceUnreachable', fields={'error': serializers.CharField()}),
        }
    )
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
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Submit a job application with resume file",
        description="Creates/updates a candidate profile, records job application, and emits an Outbox event for Kafka sync.",
        request=inline_serializer(
            name='JobApplicationRequest',
            fields={
                'email': serializers.EmailField(required=True),
                'full_name': serializers.CharField(required=True),
                'job_id': serializers.IntegerField(required=True),
                'skills': serializers.CharField(required=False, allow_blank=True),
                'resume': serializers.FileField(required=True, help_text="PDF/Docx resume file upload"),
            }
        ),
        responses={
            201: inline_serializer(
                name='JobApplicationSuccess',
                fields={
                    'message': serializers.CharField(),
                    'application': serializers.IntegerField(help_text="Created Application ID"),
                    'status': serializers.CharField(),
                }
            ),
            400: inline_serializer('JobApplicationBadRequest', fields={'error': serializers.CharField()}),
        }
    )
    def post(self, request):
        email = request.data.get("email")
        full_name = request.data.get("full_name")
        job_id = request.data.get("job_id")
        skills = request.data.get("skills")
        resume = request.FILES.get('resume')
        
        if not email or not full_name or not job_id or not resume:
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
            application = JobApplication.objects.create(
                candidate=candidate, 
                job_id=job_id,
                resume=resume
            )
            unique_event_id = str(uuid.uuid4())
            payload = {
                "event_id": unique_event_id,
                "event": "application_created",
                "user_application_id": application.id,
                "candidate_name": candidate.full_name,
                "candidate_email": candidate.email,
                "job_id": job_id,
                "resume_url": application.resume.url
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
                channel='user_events',
                payload=payload,
                extra=extra
            )
        
        return Response({
            "message": "Application submitted successfully",
            "application": application.id,
            "status": application.status,
        }, status=status.HTTP_201_CREATED)
            
        