from rest_framework import serializers
from .models import JobPosting, AdminApplicationReview

class JobPostingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosting
        fields = [
            'id',
            'title',
            'department',
            'description',
            'is_active',
            'created_at'
        ]
        
class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminApplicationReview
        fields = [
            'user_application_id',
            'candidate_name',
            'candidate_email',
            'review_status',
            'resume_url'
        ]