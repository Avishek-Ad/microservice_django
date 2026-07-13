from rest_framework import serializers
from .models import JobPosting

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