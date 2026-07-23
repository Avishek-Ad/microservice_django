from django.db import models
from django.db.models import JSONField
from pathlib import Path
from django.core.validators import FileExtensionValidator
import uuid

def generate_resume_storage_path(filename: str) -> str:
    file_path = Path(filename)
    random_short_code = uuid.uuid4().hex[:8]  # e.g., "f3b89a2c"
    
    # Store it inside a clean folder structure, e.g., "documents/resumes/"
    return f"{file_path.stem}-{random_short_code}{file_path.suffix}"


def user_directory_path(instance, filename):
    file_path = Path(filename)
    random_short_code = uuid.uuid4().hex[:8] # "f3b89a2c"
    return f"{file_path.stem}-{random_short_code}{file_path.suffix}"

class CandidateProfile(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    skills = models.TextField(help_text="comma seperated skills eg; python,django")
    
    def __str__(self):
        return self.full_name
    
class JobApplicationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "Approved", "approved"
    REJECTED = "Rejected", "rejected"
    
    
class JobApplication(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)
    job_id = models.IntegerField() # job id from admin services
    status = models.CharField(
        max_length=8, 
        choices=JobApplicationStatus.choices,
        default=JobApplicationStatus.PENDING
    )
    resume=models.FileField(
        upload_to=user_directory_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])], 
        null=True, 
        blank=True
    ) # "documents/resume-f3b89a2c.pdf"
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Application {self.id} for job {self.job_id} by {self.candidate.email}"
    
class PublishedEvent(models.Model):
    channel = models.CharField(max_length=200)
    payload = JSONField(default=dict, blank=True)
    extra = JSONField(default=dict, blank=True)
    is_consumed = models.BooleanField(default=False)
    
    def __str__(self):
        return self.channel
    
class ProcessedEvent(models.Model):
    event_id = models.UUIDField(primary_key=True) 
    processed_at = models.DateTimeField(auto_now_add=True)