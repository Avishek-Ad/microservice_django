from django.db import models
from django.db.models import JSONField

class JobPosting(models.Model):
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} {self.department}"
    
class AdminApplicationReviewStatus(models.TextChoices):
    NEW = 'new_application', 'New Application'
    UNDER_REVIEW = 'under_review', 'Under Review'
    HIRED = 'hired', 'Hired'
    REJECTED = 'rejected', 'Rejected'
    
class AdminApplicationReview(models.Model):
    user_application_id = models.IntegerField() # application id form user_service
    candidate_name = models.CharField(max_length=200)
    candidate_email = models.EmailField()
    job = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='applications')
    review_status = models.CharField(
        max_length=20, 
        choices=AdminApplicationReviewStatus.choices,
        default=AdminApplicationReviewStatus.NEW
        )
    logged_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review for {self.candidate_email} - Job: {self.job.title}"
    

class PublishedEvent(models.Model):
    channel = models.CharField(max_length=200)
    payload = JSONField()
    extra = JSONField(default=dict, blank=True)
    is_consumed = models.BooleanField(default=False)
    
    def __str__(self):
        return self.channel

class ProcessedEvent(models.Model):
    event_id = models.UUIDField(primary_key=True) 
    processed_at = models.DateTimeField(auto_now_add=True)
    