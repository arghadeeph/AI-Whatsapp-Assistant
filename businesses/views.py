from django.shortcuts import render
from .models import FAQ
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import FAQSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404


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