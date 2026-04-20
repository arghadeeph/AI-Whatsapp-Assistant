import openai
from django.conf import settings
from messaging.models import Messages
import logging

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

logger = logging.getLogger(__name__)

def build_system_prompt(business):
    """Build a tenant-specific system prompt."""
    return (
        f"You are a helpful WhatsApp assistant for {business.name}. "
        f"{getattr(business, 'ai_instructions', '')} "
        "Be concise and friendly. Respond in plain text without markdown."
    )

def get_conversation_history(business, contact_phone, limit=5):
    """Fetch the last N messages for a contact as OpenAI message dicts."""
    messages = (
        Messages.objects
        .filter(business=business, phone=contact_phone)
        .order_by("-created_at")[:limit]
    )
    # Reverse so oldest-first for the API
    def map_role(sender):
        if sender == "user":
            return "user"
        else:  # "ai" or "business" — both are assistant from OpenAI's perspective
            return "assistant"
    
    return [
        {
            "role": map_role(msg.sender),
            "content": msg.message
        }
        for msg in reversed(list(messages))
    ]

def get_ai_response(business, contact_phone, user_message):

    """
    Call GPT with conversation history and return the assistant reply string.
    Raises openai.OpenAIError on failure — caller should handle this.
    """
    history = get_conversation_history(business, contact_phone)

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": build_system_prompt(business)},
            *history,
            {"role": "user", "content": user_message},  # current message
        ],
    )
    return response.choices[0].message.content.strip()