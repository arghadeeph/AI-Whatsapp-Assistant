from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Max
from .models import Messages, ConversationState
from .utils import sign_phone,unsign_phone
from django.utils import timezone
from .services import send_whatsapp_message
from django.shortcuts import render
from django.http import JsonResponse
from businesses.models import Business
from users.models import UserBusiness



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
            state = ConversationState.objects.filter(business=business, phone=c['phone']).first()
            last_read_at = state.last_read_at if state else None
            last_out = (
                Messages.objects
                .filter(business=business, phone=c['phone'], direction='out')
                .aggregate(last_out=Max('created_at'))['last_out']
            )
            unread_since = last_read_at or last_out
            unread_count = (
                Messages.objects
                .filter(
                    business=business,
                    phone=c['phone'],
                    direction='in',
                    created_at__gt=unread_since if unread_since else c['last_time']
                )
                .count()
            )
            latest_inbound = (
                Messages.objects
                .filter(
                    business=business,
                    phone=c['phone'],
                    direction='in',
                )
                .order_by('-created_at')
                .values('message')
                .first()
            )
            data.append({
                "phone": c['phone'],
                "signed_phone": sign_phone(c['phone']),
                "last_time": c['last_time'].strftime("%H:%M") if c['last_time'] else "",
                "unread_count": unread_count,
                "has_unread": unread_count > 0,
                "last_read_at": last_read_at.isoformat() if last_read_at else None,
                "latest_inbound_message": latest_inbound["message"] if latest_inbound else "",
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
                "timestamp": timezone.localtime(m.timestamp).strftime("%H:%M")
            }
            for m in messages
        ]

        return Response({"messages": data})


class MarkConversationReadAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        business = request.business
        signed_phone = request.data.get("phone")
        phone = unsign_phone(signed_phone)
        if not phone:
            return Response({"error": "Invalid phone"}, status=403)

        state, _ = ConversationState.objects.get_or_create(
            business=business,
            phone=phone,
        )
        state.last_read_at = timezone.now()
        state.save(update_fields=["last_read_at", "updated_at"])

        return Response({"status": "ok"})
    

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


class AIReplyToggleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        business = request.business
        ai_enabled = request.data.get("ai_enabled")

        if ai_enabled is None:
            business.ai_enabled = not business.ai_enabled
        else:
            business.ai_enabled = str(ai_enabled).lower() in ("1", "true", "yes", "on")

        business.save(update_fields=["ai_enabled"])

        return Response({
            "ai_enabled": business.ai_enabled,
            "message": "AI reply setting updated successfully."
        })

    
def chat_list_page(request):
    return render(request, 'messaging/chat_list.html')


def chat_page(request, signed_phone):
    phone = unsign_phone(signed_phone)
    business = getattr(request, "business", None)
    if business is None and request.user.is_authenticated:
        user_business = (
            UserBusiness.objects
            .select_related("business")
            .filter(user=request.user)
            .first()
        )
        business = user_business.business if user_business else None

    return render(request, 'messaging/chat.html', {
        'signed_phone': signed_phone,
        'phone': phone or 'Unknown number',
        'ai_enabled': getattr(business, 'ai_enabled', True),
    })
