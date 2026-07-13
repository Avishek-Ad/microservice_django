from django.db import models

class candidateProfile(models.Model):
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    skills = models.TextField(help_text="comma seperated skills eg; python,django")
    
    def __str__(self):
        