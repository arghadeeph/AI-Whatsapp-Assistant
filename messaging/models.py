from django.db import models
from businesses.models import Business

# Create your models here.
class Messages(models.Model):

    business = models.ForeignKey(Business, on_delete=models.CASCADE)

    phone = models.CharField(max_length=20)

    sender_name  = models.CharField(max_length=255, null=True, blank=True)

    sender = models.CharField(
        max_length=10,
        choices=[
            ('user', 'User'),
            ('ai', 'AI'),
            ('business', 'Business'),
        ]
    )

    message = models.TextField()

    message_type = models.CharField(
        max_length=20,
        default='text'
    )

    direction = models.CharField(
        max_length=10,
        choices=[
            ('in', 'Incoming'),
            ('out', 'Outgoing')
        ]
    )

    wa_message_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        default='received'
    )

    timestamp = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone} ({self.sender}) - {self.message[:30]}"

    class Meta:
        indexes = [
            models.Index(fields=['business', 'phone']),
        ]