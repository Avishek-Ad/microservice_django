from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from .models import JobPosting, AdminApplicationReview, AdminApplicationReviewStatus
from .serializers import JobPostingSerializer, JobApplicationSerializer

class PublicAdminJobListAPIView(APIView):
    """
    For fetching active jobs by user_service
    """
    def get(self, response):
        jobs = JobPosting.objects.filter(is_active=True).order_by('-created_at')
        serializer = JobPostingSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class JobListCreateAPIView(
    generics.ListCreateAPIView
):
    queryset = JobPosting.objects.all()
    serializer_class = JobPostingSerializer
    
class JobRetriveUpdateDestroyAPIView(
    generics.RetrieveUpdateDestroyAPIView
):
    queryset = JobPosting.objects.all()
    serializer_class = JobPostingSerializer
    lookup_field = "pk"
    
class JobApplicationsListAPIView(APIView):
    def get(self, request, job_id):
        try:
            job_posting = JobPosting.objects.get(id=job_id)
            applications = job_posting.applications.all()
            serializer = JobApplicationSerializer(applications, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except JobPosting.DoesNotExist:
            return Response({"message": f"Job posting with id {job_id} not found"}, status=status.HTTP_404_NOT_FOUND)
        
class JobApplicationsStatusChange(APIView):
    def post(self, request, job_id, user_app_id):
        new_status = request.data.get("status", '')
        try:
            job_posting = JobPosting.objects.get(id=job_id)
            application = job_posting.applications.get(user_application_id=user_app_id)
            if new_status == "under_review":
                application.review_status = AdminApplicationReviewStatus.UNDER_REVIEW,
            elif new_status == "hired":
                application.review_status = AdminApplicationReviewStatus.HIRED
            elif new_status == "rejected":
                application.review_status = AdminApplicationReviewStatus.REJECTED
            else:
                return Response({"message": "the given status was not among accepted status"}, status=status.HTTP_400_BAD_REQUEST)
        except job_posting.DoesNotExist or AdminApplicationReview.DoesNotExist:
            return Response({"message": f"Job Application of job_id {job_id} and application_id {user_app_id} not found"}, status=status.HTTP_404_NOT_FOUND)
                