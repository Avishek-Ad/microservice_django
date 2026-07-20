from django.contrib import admin
from .models import JobPosting, AdminApplicationReview, PublishedEvent
from django.utils.html import format_html

admin.site.register(PublishedEvent)

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
    fields = [
        'user_application_id', 
        'candidate_email', 
        'review_status', 
        'resume_url',
        'preview_resume',
        'logged_at'
    ]
    readonly_fields = ["logged_at", "preview_resume"]
    list_filter = ['review_status', 'logged_at']
    search_fields = ['candidate_email', 'candidate_name']
    
    def get_job_title(self, obj):
        return obj.job.title
    get_job_title.short_description = 'Job Title' # changing header name
    
    def preview_resume(self, obj):
        if not obj.resume_url:
            return "No resume file uploaded."
        
        return format_html(
            '<iframe src="{}" width="100%" height="400px" style="border: 1px solid #ccc; border-radius: 4px;"></iframe>',
            obj.resume_url
        )
    preview_resume.short_description = "Resume Live Preview"