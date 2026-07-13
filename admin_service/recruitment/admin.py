from django.contrib import admin
from .models import JobPosting, AdminApplicationReview

@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'department', 'is_active', 'created_at']
    list_filter = ['is_active', 'department']
    search_fields = ['title', 'department']
    
@admin.register(AdminApplicationReview)
class AdminApplicationReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id', 
        'user_application_id', 
        'candidate_email', 
        'get_job_title', 
        'review_status', 
        'logged_at'
    ]
    list_filter = ['review_status', 'logged_at']
    search_fields = ['candidatecandidate_email_email', 'candidate_name']
    
    def get_job_title(self, obj):
        return obj.job.title
    get_job_title.short_description = 'Job Title' # changing header name