import logging
from businesses.models import Business
from django.conf import settings
import requests

logger = logging.getLogger(__name__)

def send_whatsapp_message(business, to_phone, message_text):
    """
    Send WhatsApp message using Cloud API
    """
    url = f"https://graph.facebook.com/v18.0/{business.phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",  # store this in DB later
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {
            "body": message_text
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        logger.info("WhatsApp send response: %s", data)

        if response.status_code != 200:
            logger.error("WhatsApp API error: %s", data)
            return None

        return data

    except Exception as e:
        logger.error("Send message error: %s", str(e))
        return None