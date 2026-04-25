import openai
from django.conf import settings
from messaging.models import Messages
import logging
from businesses.models import FAQ
from django.utils import timezone
from zoneinfo import ZoneInfo

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

logger = logging.getLogger(__name__)

def build_system_prompt(business, faq_context=""):
    """Build a tenant-specific system prompt."""
    business_tz = ZoneInfo(getattr(settings, "TIME_ZONE", "UTC") or "UTC")
    if str(business_tz) == "UTC":
        business_tz = ZoneInfo("Asia/Kolkata")
    now = timezone.localtime(timezone.now(), business_tz)
    return (
        f"You are a helpful WhatsApp assistant for {business.name}. "
        f"Current date and time: {now.strftime('%A, %B %d, %Y %I:%M %p %Z')}. "
        "Use this time only as reference for answering time-sensitive questions. "
        "Do not invent or guess the current time if you are unsure. "
        f"{getattr(business, 'ai_instructions', '')} "
        f"{faq_context} "
        "Use the FAQ information when relevant. "
        "If information is unavailable, politely ask the customer for more details. "
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

def get_relevant_faq_context(business, user_message, limit=5):
    """
    Match FAQs using both question + answer content.
    Simple keyword-based search for now.
    Later this can be upgraded to embeddings/vector search.
    """

    faqs = FAQ.objects.filter(
        business=business,
        is_active=True
    )

    matched_faqs = []
    user_words = user_message.lower().split()

    for faq in faqs:
        searchable_text = f"{faq.question} {faq.answer}".lower()

        # Match if any word from user message exists in question OR answer
        if any(word in searchable_text for word in user_words):
            matched_faqs.append(faq)

        if len(matched_faqs) >= limit:
            break

    if not matched_faqs:
        return ""

    faq_context = "\nRelevant FAQs:\n\n"

    for faq in matched_faqs:
        faq_context += f"Q: {faq.question}\n"
        faq_context += f"A: {faq.answer}\n\n"

    return faq_context.strip()


def get_ai_response(business, contact_phone, user_message):

    """
    Call GPT with conversation history and return the assistant reply string.
    Raises openai.OpenAIError on failure — caller should handle this.
    """
    history = get_conversation_history(business, contact_phone)

    faq_context = get_relevant_faq_context(
        business=business,
        user_message=user_message
    )
    
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": build_system_prompt(business, faq_context)},
            *history,
            {"role": "user", "content": user_message},  # current message
        ],
    )
    return response.choices[0].message.content.strip()
