# workers/tasks.py

import os
import requests
from celery import Celery
from datetime import datetime

from services.preprocessing import DocumentPreprocessor
from app.models import Document, ProcessingResult
from app.database import SessionLocal

# Environment-based configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ANALYSIS_API_URL = os.getenv("ANALYSIS_API_URL", "http://localhost:8001")
EMAIL_API_URL = os.getenv("EMAIL_API_URL", "http://localhost:8002")
RPA_API_URL = os.getenv("RPA_API_URL", "http://localhost:8003")

# 1) Instantiate Celery with env-based broker/backend
celery_app = Celery(
    "document_processing",
    broker=REDIS_URL,
    backend=REDIS_URL,
)


@celery_app.task
def process_document(file_path: str):
    """Main document processing task"""
    db = SessionLocal()
    try:
        # Save document to database
        filename = os.path.basename(file_path)
        document = Document(
            filename=filename,
            file_path=file_path,
            status="processing"
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        # Extract & normalize text
        if filename.lower().endswith('.pdf'):
            text = DocumentPreprocessor.extract_text_from_pdf(file_path)
        elif filename.lower().endswith('.eml'):
            text = DocumentPreprocessor.extract_text_from_eml(file_path)
        else:
            raise ValueError(f"Unsupported file type: {filename}")

        normalized_text = DocumentPreprocessor.normalize_text(text)

        # Send to analysis service
        resp = requests.post(
            f"{ANALYSIS_API_URL}/analyze",
            json={"document_id": document.id, "text": normalized_text}
        )
        resp.raise_for_status()
        data = resp.json()
        overall_score = data.get("scores", {}).get("overall")
        if overall_score is None:
            raise ValueError("Analysis service returned no overall score")

        print(f"[process_document] doc={document.id} score={overall_score}")
        # Update status & chain tasks
        if overall_score >= 8:
            document.status = "auto_approved"
            celery_app.send_task(
                'workers.tasks.auto_approve_document',
                args=[document.id]
            )
        elif overall_score >= 4:
            document.status = "quick_review"
        else:
            document.status = "manual_review"

        document.processed_at = datetime.utcnow()
        db.commit()

        return {"status": "completed", "document_id": document.id}

    except Exception:
        if 'document' in locals():
            document.status = "error"
            db.commit()
        raise
    finally:
        db.close()


@celery_app.task
def auto_approve_document(document_id: int):
    """Auto-approve high-scoring documents and queue email prep"""
    celery_app.send_task(
        'workers.tasks.prepare_email',
        args=[document_id]
    )
    return {"status": "auto_approved", "document_id": document_id}

@celery_app.task
def prepare_email(document_id: int):
    """Prepare internal email for processed document"""
    resp = requests.post(
        f"{EMAIL_API_URL}/prepare_email",
        params={"document_id": document_id}
    )
    resp.raise_for_status()
    celery_app.send_task(
        'workers.tasks.send_email_via_rpa',
        args=[document_id]
    )
    return {"status": "email_prepared", "document_id": document_id}

@celery_app.task
def send_email_via_rpa(document_id: int):
    resp = requests.post(
        f"{RPA_API_URL}/send_email",
        params={"document_id": document_id}
    )
    # debug:
    print(f"[send_email_via_rpa] → {resp.request.method} {resp.request.url}")
    if resp.status_code == 422:
        print(f"[send_email_via_rpa] 422 body: {resp.text}")
    resp.raise_for_status()
    return {"status": "email_sent", "document_id": document_id}
