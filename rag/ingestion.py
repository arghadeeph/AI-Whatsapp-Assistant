import logging
from pathlib import Path
from typing import Optional
import tempfile, os

from django.utils import timezone
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from django.conf import settings

from businesses.models import Document, DocumentChunk, FAQ

logger = logging.getLogger(__name__)

# ── Shared embeddings client (reuse across calls) ─────────────────────────────
embeddings_client = OpenAIEmbeddings(
    model="text-embedding-3-small",     # 1536 dims, cheap, fast
    openai_api_key=settings.OPENAI_API_KEY,
)

# ── Text splitter config ───────────────────────────────────────────────────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,         # tokens approx (conservative)
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " ", ""],
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD — extract raw text from file
# ─────────────────────────────────────────────────────────────────────────────
def load_document(document: Document) -> list:
    """
    Returns a list of LangChain Document objects with page_content + metadata.
    """
    file_path = document.file.path   # absolute path via MEDIA_ROOT
    mime      = document.mime_type

    if mime == "application/pdf":
        loader = PyPDFLoader(file_path)

    elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        loader = Docx2txtLoader(file_path)

    elif mime in ("text/plain", "text/markdown"):
        loader = TextLoader(file_path, encoding="utf-8")

    else:
        raise ValueError(f"Unsupported mime type: {mime}")

    pages = loader.load()
    logger.info(f"[ingest] Loaded {len(pages)} pages from '{document.title}'")
    return pages


# ─────────────────────────────────────────────────────────────────────────────
# 2. CHUNK — split pages into overlapping chunks
# ─────────────────────────────────────────────────────────────────────────────
def chunk_pages(pages: list, document: Document) -> list[dict]:
    """
    Returns list of dicts: {content, chunk_index, metadata}
    metadata is stored on DocumentChunk for citations later.
    """
    raw_chunks = splitter.split_documents(pages)

    chunks = []
    for i, chunk in enumerate(raw_chunks):
        chunks.append({
            "chunk_index": i,
            "content": chunk.page_content.strip(),
            "metadata": {
                "doc_title": document.title,
                "doc_type":  document.doc_type,
                "doc_id":    str(document.id),
                "page":      chunk.metadata.get("page", None),
            },
        })

    logger.info(f"[ingest] Split into {len(chunks)} chunks")
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# 3. EMBED — call OpenAI, get vectors back
# ─────────────────────────────────────────────────────────────────────────────
def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Batch embed. OpenAI allows up to 2048 texts per call.
    We batch in 200s to stay safe.
    """
    BATCH = 200
    all_embeddings = []
    for i in range(0, len(texts), BATCH):
        batch = texts[i : i + BATCH]
        vecs  = embeddings_client.embed_documents(batch)
        all_embeddings.extend(vecs)
        logger.info(f"[embed] Embedded batch {i}–{i+len(batch)}")
    return all_embeddings


# ─────────────────────────────────────────────────────────────────────────────
# 4. STORE — bulk-create DocumentChunk rows
# ─────────────────────────────────────────────────────────────────────────────
def store_chunks(chunks: list[dict], embeddings: list, document: Document):
    # Delete old chunks first (re-ingestion safe)
    DocumentChunk.objects.filter(document=document).delete()

    objs = [
        DocumentChunk(
            document    = document,
            business    = document.business,          # denormalized
            chunk_index = c["chunk_index"],
            content     = c["content"],
            embedding   = embeddings[idx],
            metadata    = c["metadata"],
        )
        for idx, c in enumerate(chunks)
    ]

    DocumentChunk.objects.bulk_create(objs, batch_size=200)
    logger.info(f"[ingest] Stored {len(objs)} chunks for '{document.title}'")


# ─────────────────────────────────────────────────────────────────────────────
# 5. ORCHESTRATOR — call this from your Celery task
# ─────────────────────────────────────────────────────────────────────────────
def ingest_document(document_id: str) -> None:
    try:
        document = Document.objects.select_related("business").get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"[ingest] Document {document_id} not found")
        return

    logger.info(f"[ingest] Starting ingestion for '{document.title}'")

    pages    = load_document(document)
    chunks   = chunk_pages(pages, document)
    # Include document title and type in the embedded text so queries like
    # "what is return policy?" can match a section even when the chunk body
    # does not repeat the exact heading.
    texts    = [
        f"{document.title}\n{document.doc_type}\n{c['content']}"
        for c in chunks
    ]
    vecs     = embed_texts(texts)

    store_chunks(chunks, vecs, document)

    # Mark as ingested
    document.ingested_at = timezone.now()
    document.save(update_fields=["ingested_at"])
    logger.info(f"[ingest] Done — '{document.title}'")


# ─────────────────────────────────────────────────────────────────────────────
# 6. FAQ BACKFILL — embed all un-embedded FAQs for a business
# ─────────────────────────────────────────────────────────────────────────────
def backfill_faq_embeddings(business_id: str) -> None:
    faqs = FAQ.objects.filter(
        business_id=business_id,
        is_active=True,
        embedding=None,         # only un-embedded ones
    )

    if not faqs.exists():
        logger.info(f"[backfill] No FAQs to embed for business {business_id}")
        return

    texts = [f"{faq.question}\n{faq.answer}" for faq in faqs]
    vecs  = embed_texts(texts)

    for faq, vec in zip(faqs, vecs):
        faq.embedding    = vec
        faq.embedded_at  = timezone.now()

    FAQ.objects.bulk_update(faqs, ["embedding", "embedded_at"], batch_size=200)
    logger.info(f"[backfill] Embedded {len(faqs)} FAQs for business {business_id}")
