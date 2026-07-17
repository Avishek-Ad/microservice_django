from django.db import models
from django.contrib.postgres.fields import JSONField

class SystemLogType(models.TextChoices):
    HTTP = "HTTP", "HTTP Connection"
    EVENT = "EVENT", "Streamed Event"

class SystemLog(models.Model):
    log_type = models.CharField(
        max_length=10, 
        choices=SystemLogType.choices, 
        default=SystemLogType.EVENT
    )
    sender = models.CharField(max_length=200)
    receiver = models.CharField(max_length=200)
    
    event_type = models.CharField(max_length=200) # e.g, POST or "update_satus"
    
    payload = JSONField()
    
    occured_at = models.DateTimeField()
    
    def __str__(self):
        return f"{self.log_type} from {self.sender} to {self.receiver} with event {self.event_type}"