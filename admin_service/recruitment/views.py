from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from .models import JobPosting, AdminApplicationReview, AdminApplicationReviewStatus
from .serializers import JobPostingSerializer, JobApplicationSerializer
from rest_framework import serializers

class PublicAdminJobListAPIView(APIView):
    """
    For fetching active jobs by user_service
    """
    @extend_schema(
        summary="Fetch active job postings",
        responses={200: JobPostingSerializer(many=True)}
    )
    def get(self, request):
        jobs = JobPosting.objects.filter(is_active=True).order_by('-created_at')
        serializer = JobPostingSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class JobListCreateAPIView(
    generics.ListCreateAPIView
):
    queryset = JobPosting.objects.all()
    serializer_class = JobPostingSerializer
    
class JobRetriveUpdateAPIView(
    generics.RetrieveUpdateAPIView
):
    queryset = JobPosting.objects.all()
    serializer_class = JobPostingSerializer
    lookup_field = "pk"
    
class JobDeleteThroughPostAPIView(APIView):
    @extend_schema(
        summary="Delete a job posting via POST",
        description="Deletes a specific job posting based on the provided primary key (pk) in the URL route path.",
        responses={
            # Documenting the 204 No Content response
            status.HTTP_204_NO_CONTENT: OpenApiResponse(
                description="Job posting successfully deleted. No content is returned."
            ),
            # Documenting the 404 Error response structure
            status.HTTP_404_NOT_FOUND: OpenApiResponse(
                description="The specified job posting could not be found.",
                # DRF automatically formats errors with a {"detail": "..."} schema
            ),
        },
        # If your endpoint doesn't require a JSON body (since it relies on the URL path pk),
        # setting request=None prevents Swagger from rendering an empty JSON text area box.
        request=None 
    )
    def post(self, request, pk):
        try:
            job_post = JobPosting.objects.get(pk=pk)
            job_post.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except JobPosting.DoesNotExist:
            return Response(
                {"detail": "Job posting not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
    
class JobApplicationsListAPIView(APIView):
    @extend_schema(
        summary="List all applications for a specific job",
        responses={
            200: JobApplicationSerializer(many=True),
            404: inline_serializer('JobNotFound', fields={'message': serializers.CharField()})
        }
    )
    def get(self, request, job_id):
        try:
            job_posting = JobPosting.objects.get(id=job_id)
            applications = job_posting.applications.all()
            serializer = JobApplicationSerializer(applications, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except JobPosting.DoesNotExist:
            return Response({"message": f"Job posting with id {job_id} not found"}, status=status.HTTP_404_NOT_FOUND)
        
class JobApplicationsStatusChange(APIView):
    @extend_schema(
        summary="Update applicant review status",
        request=inline_serializer(
            name='JobStatusChangeRequest',
            fields={
                'new_status': serializers.ChoiceField(
                    choices=['under_review', 'hired', 'rejected'],
                    help_text="Target status for application review"
                )
            }
        ),
        responses={
            200: inline_serializer('StatusChangeSuccess', fields={'message': serializers.CharField()}),
            400: inline_serializer('StatusChangeBadRequest', fields={'message': serializers.CharField()}),
            404: inline_serializer('StatusChangeNotFound', fields={'message': serializers.CharField()}),
        }
    )
    def post(self, request, job_id, user_app_id):
        new_status = request.data.get("new_status", '')
        try:
            job_posting = JobPosting.objects.get(id=job_id)
            application = job_posting.applications.get(user_application_id=user_app_id)
            if new_status == "under_review":
                application.review_status = AdminApplicationReviewStatus.UNDER_REVIEW
            elif new_status == "hired":
                application.review_status = AdminApplicationReviewStatus.HIRED
            elif new_status == "rejected":
                application.review_status = AdminApplicationReviewStatus.REJECTED
            else:
                return Response({"message": "the given status was not among accepted status"}, status=status.HTTP_400_BAD_REQUEST)
            application.save()
            return Response({"message": f"{user_app_id} is {new_status} for job id {job_id}"}, status=status.HTTP_200_OK)
        except (JobPosting.DoesNotExist, AdminApplicationReview.DoesNotExist):
            return Response({"message": f"Job Application of job_id {job_id} and application_id {user_app_id} not found"}, status=status.HTTP_404_NOT_FOUND)
                