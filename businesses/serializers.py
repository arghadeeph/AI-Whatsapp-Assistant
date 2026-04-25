from rest_framework import serializers
from .models import FAQ, Document, DocumentChunk

class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model  = FAQ
        fields = ['id', 'question', 'answer', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        faq = super().create(validated_data)
        faq.embedding = None
        faq.embedded_at = None
        faq.save(update_fields=["embedding", "embedded_at"])
        return faq

    def update(self, instance, validated_data):
        faq = super().update(instance, validated_data)
        faq.embedding = None
        faq.embedded_at = None
        faq.save(update_fields=["embedding", "embedded_at"])
        return faq


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Document
        fields = [
            "id", "title", "doc_type", "file",
            "description", "metadata", "is_active",
            "file_name", "mime_type", "file_size_bytes",
            "ingested_at", "created_at",
        ]
        read_only_fields = ["id", "file_name", "mime_type",
                            "file_size_bytes", "ingested_at", "created_at"]

    def validate_file(self, value):
        max_bytes = 20 * 1024 * 1024  # 20 MB
        if value.size > max_bytes:
            raise serializers.ValidationError("File too large. Max 20 MB.")
        allowed = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
        ]
        if value.content_type not in allowed:
            raise serializers.ValidationError(
                "Unsupported file type. Upload PDF, DOCX, or TXT."
            )
        return value

    def create(self, validated_data):
        file = validated_data["file"]
        validated_data["file_name"]       = file.name
        validated_data["mime_type"]       = file.content_type
        validated_data["file_size_bytes"] = file.size
        return super().create(validated_data)


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model  = DocumentChunk
        fields = ["id", "chunk_index", "content", "metadata"]


class DocumentDetailSerializer(serializers.ModelSerializer):
    chunks      = DocumentChunkSerializer(many=True, read_only=True)
    is_ingested = serializers.BooleanField(read_only=True)
    file_url    = serializers.SerializerMethodField()

    class Meta:
        model  = Document
        fields = [
            "id", "title", "doc_type", "file", "file_name",
            "file_url", "description", "is_active", "is_ingested",
            "ingested_at", "created_at", "chunks",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return None
        url = obj.file.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
