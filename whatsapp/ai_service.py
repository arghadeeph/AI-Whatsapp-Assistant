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
RAG_FAQ_MAX_DISTANCE = getattr(settings, "RAG_FAQ_MAX_DISTANCE", getattr(settings, "RAG_MAX_DISTANCE", 0.40))
RAG_DOC_MAX_DISTANCE = getattr(settings, "RAG_DOC_MAX_DISTANCE", getattr(settings, "RAG_MAX_DISTANCE", 0.60))
RAG_QUERY_MIN_CHARS = getattr(settings, "RAG_QUERY_MIN_CHARS", 3)

def _vector_literal(vector):
    return "[" + ",".join(str(v) for v in vector) + "]"


def _normalize_query(text: str) -> str:
    """
    Normalize user text before embedding so trivial punctuation and spacing
    differences do not reduce retrieval quality.
    """
    text = " ".join((text or "").split())
    return text.strip()


def _get_query_embedding(user_message):
    return embeddings_client.embed_query(_normalize_query(user_message))


def _truncate(text, limit=RAG_SNIPPET_CHARS):
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def get_retrieval_context(business, user_message, faq_limit=FAQ_RAG_LIMIT, chunk_limit=DOC_RAG_LIMIT):
    """
    Retrieve top FAQ and document chunk matches using pgvector similarity search.
    """
    normalized_message = _normalize_query(user_message)
    if len(normalized_message) < RAG_QUERY_MIN_CHARS:
        logger.info(
            "RAG skipped | business=%s | query too short after normalization | raw=%s",
            business.id,
            _truncate(user_message, 80),
        )
        return ""

    query_embedding = _vector_literal(_get_query_embedding(normalized_message))

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
              AND (embedding <=> %s::vector) <= %s
            ORDER BY distance ASC
            LIMIT %s
            """,
            [query_embedding, business.id, query_embedding, RAG_FAQ_MAX_DISTANCE, faq_limit],
        )
        faqs = cursor.fetchall()

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT dc.id, dc.content, d.title, d.doc_type, (dc.embedding <=> %s::vector) AS distance
            FROM {chunk_table} dc
            JOIN {document_table} d
              ON dc.document_id = d.id
            WHERE dc.business_id = %s
              AND dc.embedding IS NOT NULL
              AND (dc.embedding <=> %s::vector) <= %s
            ORDER BY distance ASC
            LIMIT %s
            """,
            [query_embedding, business.id, query_embedding, RAG_DOC_MAX_DISTANCE, chunk_limit],
        )
        chunks = cursor.fetchall()

    faq_context = ""
    if faqs:
        faq_context += "\nFAQ Matches:\n"
        for faq_id, question, answer, distance in faqs:
            logger.info(
                "RAG FAQ match | business=%s | faq_id=%s | distance=%.4f | question=%s | answer=%s",
                business.id,
                faq_id,
                distance,
                _truncate(question, 70),
                _truncate(answer, 70),
            )
            faq_context += f"- {question} :: {_truncate(answer)}\n"
    else:
        logger.info("RAG FAQ match | business=%s | no matches under distance %.2f", business.id, RAG_FAQ_MAX_DISTANCE)

    doc_context = ""
    if chunks:
        doc_context += "\nDocument Matches:\n"
        for chunk_id, content, title, doc_type, distance in chunks:
            logger.info(
                "RAG DOC match | business=%s | chunk_id=%s | distance=%.4f | title=%s | type=%s | content=%s",
                business.id,
                chunk_id,
                distance,
                _truncate(title, 70),
                doc_type,
                _truncate(content, 70),
            )
            doc_context += f"- {title} ({doc_type}) :: {_truncate(content)}\n"
    else:
        logger.info("RAG DOC match | business=%s | no matches under distance %.2f", business.id, RAG_DOC_MAX_DISTANCE)

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
        "Use ONLY the retrieved FAQ and document information when relevant. "
        "If there is no relevant retrieved context, say you do not know and ask a brief follow-up question. "
        "Do not invent shop hours, services, prices, names, or policies. "
        "Keep the answer short and practical. "
        "Prefer one concise paragraph or 3 bullets max. "
        "Be concise and friendly. Respond in plain text without markdown."
    )

def get_conversation_history(business, contact_phone, limit=3):
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
        max_tokens=min(settings.OPENAI_MAX_TOKENS, 300),
        temperature=settings.OPENAI_TEMPERATURE,
        messages=[
            {"role": "system", "content": build_system_prompt(business, rag_context)},
            *history,
            {"role": "user", "content": user_message},  # current message
        ],
    )
    return response.choices[0].message.content.strip()
