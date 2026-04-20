from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Max
from .models import Messages
from .utils import sign_phone,unsign_phone
from django.utils import timezone
from .services import send_whatsapp_message
from django.shortcuts import render
from django.http import JsonResponse



class ConversationListAPI(APIView):
    permission_classes = [IsAuthenticated]

   
    def get(self, request):
        business = request.business
        
        conversations = (
            Messages.objects
            .filter(business=business)
            .values('phone')
            .annotate(last_time=Max('created_at'))
            .order_by('-last_time')
        )

        data = []
        
        for c in conversations:
            data.append({
                "phone": c['phone'],
                "signed_phone": sign_phone(c['phone']),
                "last_time": c['last_time'].strftime("%H:%M") if c['last_time'] else ""
            })

        return Response({"conversations": data})
    
    
class MessagesAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, signed_phone):
        business = request.business

        phone = unsign_phone(signed_phone)
        if not phone:
            return Response({"error": "Invalid phone"}, status=403)

        messages = Messages.objects.filter(
            business=business,
            phone=phone
        ).order_by('created_at')

        data = [
            {
                "message": m.message,
                "direction": m.direction,
                "timestamp": m.timestamp.strftime("%H:%M")
            }
            for m in messages
        ]

        return Response({"messages": data})
    

class SendMessageAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        business = request.business

        signed_phone = request.data.get("phone")
        message_text = request.data.get("message")

        phone = unsign_phone(signed_phone)
        if not phone:
            return Response({"error": "Invalid phone"}, status=403)

        response = send_whatsapp_message(business, phone, message_text)

        Messages.objects.create(
            business=business,
            phone=phone,
            sender='business',
            direction='out',
            message=message_text,
            message_type='text',
            wa_message_id=response['messages'][0]['id'] if response else None,
            status='sent',
            timestamp=timezone.now()
        )

        return Response({"status": "sent"})

    
def chat_list_page(request):
    return render(request, 'messaging/chat_list.html')


def chat_page(request, signed_phone):
    return render(request, 'messaging/chat.html', {
        'signed_phone': signed_phone
    })