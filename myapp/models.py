from django.db import models

class WebhookEvent(models.Model):
    event_type = models.CharField(max_length=100)   # e.g., push, star, fork
    repo_name = models.CharField(max_length=200)    # repository name
    payload = models.JSONField()                    # full JSON payload
    received_at = models.DateTimeField(auto_now_add=True)  # timestamp

    def __str__(self):
        return f"{self.event_type} on {self.repo_name} at {self.received_at}"
