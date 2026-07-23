from django.contrib import admin
from .models import JobApplication, CandidateProfile, PublishedEvent
from django.utils.html import format_html

admin.site.register(CandidateProfile)
admin.site.register(PublishedEvent)

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["candidate", "job_id", "status", "submitted_at"]
    list_filter = ["candidate", "job_id", "status"]
    fields = [
        "candidate",
        "job_id",
        "status",
        "resume",
        "preview_resume",
        "submitted_at"
    ]
    readonly_fields = ["preview_resume", "submitted_at"]
    
    def preview_resume(self, obj):
        if not obj.resume:
            return "No resume file uploaded."
        
        return format_html(
            '<iframe src="{}" width="100%" height="400px" style="border: 1px solid #ccc; border-radius: 4px;"></iframe>',
            obj.resume.url
        )
        
    preview_resume.short_description = "Resume Live Preview"
