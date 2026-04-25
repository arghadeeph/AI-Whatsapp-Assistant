# businesses/models.py

from django.db import models
from pgvector.django import VectorField   
import uuid

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

    embedding       = VectorField(dimensions=1536, null=True, blank=True)
    embedded_at     = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.business.name} — {self.question[:50]}"    
    

class Document(models.Model):
    """Raw uploaded file — catalog, menu, policy, etc."""

    class DocType(models.TextChoices):
        CATALOG = "catalog", "Catalog"
        MENU    = "menu",    "Menu"
        POLICY  = "policy",  "Policy"
        FAQ     = "faq",     "FAQ document"
        OTHER   = "other",   "Other"

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business        = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="documents")
    title           = models.CharField(max_length=255)
    doc_type        = models.CharField(max_length=20, choices=DocType.choices)
    file            = models.FileField(upload_to="documents/%Y/%m/")  # MEDIA_ROOT path
    file_name       = models.CharField(max_length=255)
    mime_type       = models.CharField(max_length=100, blank=True)
    file_size_bytes = models.BigIntegerField(null=True, blank=True)
    description     = models.TextField(blank=True)
    metadata        = models.JSONField(default=dict, blank=True)
    is_active       = models.BooleanField(default=True)
    ingested_at     = models.DateTimeField(null=True, blank=True)  # null = not yet embedded
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["business"]),
            models.Index(fields=["business", "doc_type"]),
            models.Index(fields=["business", "is_active"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.doc_type}) — {self.business}"

    @property
    def is_ingested(self):
        return self.ingested_at is not None


class DocumentChunk(models.Model):
    """One chunk of a Document — what actually gets embedded and searched."""

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document    = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    business    = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="chunks")
    chunk_index = models.IntegerField()
    content     = models.TextField()
    embedding   = VectorField(dimensions=1536, null=True, blank=True)
    # metadata carries: page_num, section, doc_title, doc_type — useful for citations
    metadata    = models.JSONField(default=dict, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document", "chunk_index"]
        indexes  = [
            models.Index(fields=["business"]),
            models.Index(fields=["document"]),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"