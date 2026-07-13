from django.db import models

class candidateProfile(models.Model):
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
    candidate = models.ForeignKey(candidateProfile, on_delete=models.CASCADE)
    job_id = models.IntegerField() # job id from admin services
    status = models.CharField(
        max_length=8, 
        choices=JobApplicationStatus.choices, 
        default=JobApplicationStatus.PENDING
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return "Application {self.id} for job {self.job_id} by {self.candidate.email}"