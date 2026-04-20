from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from messaging.models import Messages
from businesses.models import Business


def dashboard(request):
    # HTML only; data comes from the dashboard API
    return render(request, 'dashboard/index.html')


class DashboardDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business = Business.objects.get(id=request.business_id)

        messages_count = Messages.objects.filter(business=request.business).count()
        stats = {
            'messages': messages_count,
            'leads': 0,
            'campaigns': 0,
        }

        return Response({
            'business': {
                'id': business.id,
                'name': business.name,
                'phone_number': business.phone_number,
                'tone': business.tone,
                'ai_enabled': business.ai_enabled,
            },
            'stats': stats,
        })
