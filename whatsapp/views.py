import logging
import json
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from messaging.models import Messages
from businesses.models import Business
from datetime import datetime
from messaging.services import send_whatsapp_message
from django.utils import timezone
from whatsapp.ai_service import get_ai_response
from django.utils.timezone import is_naive, make_aware

logger = logging.getLogger(__name__)


class WhatsAppWebhookView(APIView):
    """
    Handles two types of requests from Meta:
    GET  — webhook verification (one time setup)
    POST — incoming messages
    """
    permission_classes = [AllowAny]  # Meta doesn't send JWT tokens

    # ─── GET — Webhook Verification ───────────────────────────────────────────
    def get(self, request):
        """
        Meta sends a GET request to verify your webhook URL.
        You must return the hub.challenge value to confirm.
        """
        mode      = request.query_params.get('hub.mode')
        token     = request.query_params.get('hub.verify_token')
        challenge = request.query_params.get('hub.challenge')
        
        print("Webhook verification attempt:", mode, token, challenge)

        if mode == 'subscribe' and token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("Webhook verified successfully.")
            # Return challenge as plain text — Meta requires this
            from django.http import HttpResponse
            return HttpResponse(challenge, status=200)

        logger.warning("Webhook verification failed.")
        return Response({"error": "Verification failed."}, status=403)

    # ─── POST — Incoming Messages ──────────────────────────────────────────────
    def post(self, request):
        """
        Meta sends a POST request every time:
        - A user sends a message
        - A message status changes (sent, delivered, read)
        """
        try:
            payload = request.data

            # Log the full raw payload for debugging
            logger.info("Webhook received: %s", json.dumps(payload, indent=2))

            # Validate it's a WhatsApp message
            if payload.get('object') != 'whatsapp_business_account':
                return Response({"status": "ignored"}, status=200)

            # Loop through entries (usually just one)
            for entry in payload.get('entry', []):
                for change in entry.get('changes', []):

                    value = change.get('value', {})

                    # ── Handle incoming messages ──
                    messages = value.get('messages', [])
                    for message in messages:
                        self._handle_message(message, value)

                    # ── Handle status updates ──
                    statuses = value.get('statuses', [])
                    for status in statuses:
                        self._handle_status(status)

            # Always return 200 to Meta — otherwise it will retry
            return Response({"status": "ok"}, status=200)

        except Exception as e:
            logger.error("Webhook error: %s", str(e))
            # Still return 200 — we don't want Meta to keep retrying
            return Response({"status": "error"}, status=200)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _handle_message(self, message, value):
        """Parse and log incoming message."""

        msg_type    = message.get('type')           # text, image, audio etc
        from_number = message.get('from')           # sender's phone number
        msg_id      = message.get('id')             # unique message ID
        msg_timestamp   = message.get('timestamp')      # unix timestamp

        timestamp = None
        if msg_timestamp:
            timestamp = datetime.fromtimestamp(int(msg_timestamp), tz=timezone.utc)
            if is_naive(timestamp):
                timestamp = make_aware(timestamp)
            timestamp = timezone.localtime(timestamp)

        # Get sender's name from contacts
        contacts    = value.get('contacts', [])
        contact_wa_id = contacts[0].get('wa_id') if contacts else None
        sender_name = contacts[0].get('profile', {}).get('name', 'Unknown') if contacts else 'Unknown'

        # Get message body based on type
        body = ''
        if msg_type == 'text':
            body = message.get('text', {}).get('body', '')
        elif msg_type == 'image':
            body = '[Image received]'
        elif msg_type == 'audio':
            body = '[Audio received]'
        elif msg_type == 'document':
            body = '[Document received]'
        elif msg_type == 'location':
            loc  = message.get('location', {})
            body = f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"
        else:
            body = f'[{msg_type} received]'

        logger.info(
            "📩 New message | From: %s (%s) | Type: %s | Body: %s | ID: %s",
            sender_name, from_number, msg_type, body, msg_id
        )

        metadata = value.get('metadata', {})

        phone_number_id = metadata.get('phone_number_id')
        display_phone = metadata.get('display_phone_number')

        business = Business.objects.filter(phone_number_id=phone_number_id).first()

        if not business:
            business = Business.objects.filter(phone_number=display_phone).first()

        # final fallback
        if not business:
            business = Business.objects.filter(id=4).first()  # Default to business with ID 4
            
            if business:
                business.phone_number_id = phone_number_id
                business.save()

        if not business:
            logger.error(
                "No business found for phone_number_id=%s display_phone=%s",
                phone_number_id,
                display_phone,
            )
            return

        # Save to DB
        Messages.objects.create(
            business=business,
            phone=from_number,
            sender_name=sender_name,
            sender='user',
            message=body,
            message_type=msg_type,
            direction='in',
            wa_message_id=msg_id,
            status='received',
            timestamp=timestamp
        )

        # ──────REPLY─────── trigger AI reply 
        if not getattr(business, "ai_enabled", True):
            logger.info("AI reply disabled for business=%s; skipping auto response.", business.id)
            return

        try:
            reply = get_ai_response(
                business=business,
                contact_phone=from_number,
                user_message=body,
            )
        except Exception as e:
            logger.error("AI response error for %s: %s", from_number, e)
            reply = "Sorry, I'm having trouble responding right now. Please try again shortly."

        reply_to_phone = contact_wa_id or from_number

        data = send_whatsapp_message(
            business=business,
            to_phone=reply_to_phone,
            message_text=reply
        )

        wa_message_id = None
        if data:
            wa_message_id = data.get('messages', [{}])[0].get('id')
        else:
            logger.error(
                "WhatsApp send failed for business=%s recipient=%s",
                business.id,
                reply_to_phone,
            )

        Messages.objects.create(
            business=business,
            phone=reply_to_phone,
            sender='ai',
            direction='out',
            message=reply,
            message_type='text',
            wa_message_id=wa_message_id,
            status='sent' if wa_message_id else 'failed',
            timestamp=timezone.now()
        )

    def _handle_status(self, status):
        """Log message status updates."""
        msg_id     = status.get('id')
        status_val = status.get('status')  # sent, delivered, read, failed
        timestamp  = status.get('timestamp')

        Messages.objects.filter(wa_message_id=msg_id).update(status=status_val)

        logger.info("📬 Status update | Message ID: %s | Status: %s", msg_id, status_val)
