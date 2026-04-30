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


class ConversationState(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    last_read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["business", "phone"], name="unique_conversation_state")
        ]
        indexes = [
            models.Index(fields=["business", "phone"]),
        ]

    def __str__(self):
        return f"{self.business_id}:{self.phone}"
