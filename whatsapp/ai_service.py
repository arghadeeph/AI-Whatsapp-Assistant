import openai
from django.conf import settings
from messaging.models import Messages
import logging
from businesses.models import FAQ, Document, DocumentChunk
from django.utils import timezone
from zoneinfo import ZoneInfo
from langchain_openai import OpenAIEmbeddings
from django.db import connection

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
embeddings_client = OpenAIEmbeddings(
    model="text-embedding-3-small",
    openai_api_key=settings.OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)

FAQ_RAG_LIMIT = getattr(settings, "RAG_FAQ_LIMIT", 2)
DOC_RAG_LIMIT = getattr(settings, "RAG_DOCUMENT_LIMIT", 2)
RAG_SNIPPET_CHARS = 180

def _vector_literal(vector):
    return "[" + ",".join(str(v) for v in vector) + "]"


def _get_query_embedding(user_message):
    return embeddings_client.embed_query(user_message)


def _truncate(text, limit=RAG_SNIPPET_CHARS):
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def get_retrieval_context(business, user_message, faq_limit=FAQ_RAG_LIMIT, chunk_limit=DOC_RAG_LIMIT):
    """
    Retrieve top FAQ and document chunk matches using pgvector similarity search.
    """
    query_embedding = _vector_literal(_get_query_embedding(user_message))

    faq_table = FAQ._meta.db_table
    chunk_table = DocumentChunk._meta.db_table
    document_table = Document._meta.db_table

    faqs = []
    chunks = []

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT id, question, answer, (embedding <=> %s::vector) AS distance
            FROM {faq_table}
            WHERE business_id = %s
              AND is_active = TRUE
              AND embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT %s
            """,
            [query_embedding, business.id, faq_limit],
        )
        faqs = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT dc.id, dc.content, d.title, d.doc_type, (dc.embedding <=> %s::vector) AS distance
            FROM {chunk_table} dc
            JOIN {document_table} d
              ON dc.document_id = d.id
            WHERE dc.business_id = %s
              AND dc.embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT %s
            """,
            [query_embedding, business.id, chunk_limit],
        )
        chunks = cursor.fetchall()

    faq_context = ""
    if faqs:
        faq_context += "\nFAQ Matches:\n"
        for faq_id, question, answer, distance in faqs:
            logger.info(
                "RAG FAQ match | business=%s | faq_id=%s | distance=%.4f | question=%s",
                business.id,
                faq_id,
                distance,
                _truncate(question, 70),
            )
            faq_context += f"- {question} :: {_truncate(answer)}\n"

    doc_context = ""
    if chunks:
        doc_context += "\nDocument Matches:\n"
        for chunk_id, content, title, doc_type, distance in chunks:
            logger.info(
                "RAG DOC match | business=%s | chunk_id=%s | distance=%.4f | title=%s | type=%s",
                business.id,
                chunk_id,
                distance,
                _truncate(title, 70),
                doc_type,
            )
            doc_context += f"- {title} ({doc_type}) :: {_truncate(content)}\n"

    return (faq_context + doc_context).strip()


def build_system_prompt(business, rag_context=""):
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
        f"{rag_context} "
        "Use the retrieved FAQ and document information when relevant. "
        "Keep the answer short and practical. "
        "Prefer one concise paragraph or 3 bullets max. "
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

def get_ai_response(business, contact_phone, user_message):

    """
    Call GPT with conversation history and return the assistant reply string.
    Raises openai.OpenAIError on failure — caller should handle this.
    """
    history = get_conversation_history(business, contact_phone)

    rag_context = get_retrieval_context(
        business=business,
        user_message=user_message
    )
    
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        max_tokens=settings.OPENAI_MAX_TOKENS,
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": build_system_prompt(business, rag_context)},
            *history,
            {"role": "user", "content": user_message},  # current message
        ],
    )
    return response.choices[0].message.content.strip()
