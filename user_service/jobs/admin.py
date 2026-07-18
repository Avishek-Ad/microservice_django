from django.contrib import admin
from .models import JobApplication, candidateProfile, PublishedEvent

admin.site.register(candidateProfile)
admin.site.register(PublishedEvent)

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["candidate", "job_id", "status", "submitted_at"]
    list_filter = ["candidate", "job_id", "status"]
