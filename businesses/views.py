from django.shortcuts import render
from .models import FAQ, Document
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import FAQSerializer, DocumentUploadSerializer, DocumentDetailSerializer
from rest_framework import status
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
from rag.tasks import task_ingest_document


# Create your views here.

def faq_page(request):
    return render(request, 'businesses/faq.html')
 
class FAQListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = request.business
        faqs = FAQ.objects.filter(business=business).order_by('-created_at')
        serializer = FAQSerializer(faqs, many=True)
        return Response(serializer.data)

    def post(self, request):
        business = request.business
        serializer = FAQSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(business=business)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
    
class FAQDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return get_object_or_404(
            FAQ,
            pk=pk,
            business=request.business
        )

    def get(self, request, pk):
        """Retrieve a single FAQ"""
        faq = self.get_object(request, pk)
        serializer = FAQSerializer(faq)
        return Response(serializer.data)

    def put(self, request, pk):
        """Full update of an FAQ"""
        faq = self.get_object(request, pk)
        serializer = FAQSerializer(faq, data=request.data)
        if serializer.is_valid():
            serializer.save(business=request.business)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Partial update of an FAQ"""
        faq = self.get_object(request, pk)
        serializer = FAQSerializer(faq, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(business=request.business)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Optional: Delete an FAQ"""
        faq = self.get_object(request, pk)
        faq.delete()
        return Response({"message": "FAQ deleted successfully."},
                        status=status.HTTP_204_NO_CONTENT)    
    

class FAQToggleStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        faq = get_object_or_404(
            FAQ,
            pk=pk,
            business=request.business
        )

        # If is_active is provided, use it; otherwise toggle
        is_active = request.data.get('is_active')
        if is_active is None:
            faq.is_active = not faq.is_active
        else:
            faq.is_active = bool(is_active)

        faq.save(update_fields=['is_active'])

        return Response({
            "id": faq.id,
            "is_active": faq.is_active,
            "message": "FAQ status updated successfully."
        }, status=status.HTTP_200_OK)    


class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        business = request.business

        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        document = serializer.save(business=business)
        task_ingest_document.delay(str(document.id))

        return Response(DocumentUploadSerializer(document).data, status=status.HTTP_201_CREATED)


class DocumentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = request.business
        docs = Document.objects.filter(
            business=business,
            is_active=True,
        ).order_by("-created_at")
        serializer = DocumentDetailSerializer(docs, many=True)
        return Response(serializer.data)


class DocumentDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, document_id):
        business = request.business
        try:
            doc = Document.objects.get(id=document_id, business=business)
        except Document.DoesNotExist:
            return Response(status=404)

        doc.delete()
        return Response(status=204)
