from django.contrib import admin
from .models import JobApplication

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["candidate", "job_id", "status", "submitted_at"]
    list_filter = ["candidate", "job_id", "status"]
