from celery import shared_task
from .ingestion import ingest_document, backfill_faq_embeddings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def task_ingest_document(self, document_id: str):
    """Triggered automatically after every document upload."""
    try:
        ingest_document(document_id)
    except Exception as exc:
        logger.error(f"[task] Ingestion failed for {document_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2)
def task_backfill_faqs(self, business_id: str):
    """Run once per business to embed existing FAQs."""
    try:
        backfill_faq_embeddings(business_id)
    except Exception as exc:
        raise self.retry(exc=exc)