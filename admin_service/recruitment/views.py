from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import JobPosting
from .serializers import JobPostingSerializer

class PublicAdminJobListAPIView(APIView):
    """
    For fetching active jobs by user_service
    """
    def get(self, response):
        jobs = JobPosting.objects.filter(is_active=True).order_by('-created_at')
        serializer = JobPostingSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)