# businesses/models.py

from django.db import models

class Business(models.Model):
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, unique=True)
    phone_number_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    tone = models.CharField(max_length=50, default="friendly")
    ai_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class FAQ(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='faqs')
    question = models.TextField()
    answer = models.TextField()
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.business.name} — {self.question[:50]}"    