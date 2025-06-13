from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Document, ProcessingResult
from jinja2 import Template
from email_validator import validate_email, EmailNotValidError
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI(title="Email Preparation Service")


class EmailService:
    def __init__(self):
        self.email_template = Template("""
        Dear Kundeansvarlig/Assistant,

        A new document has been processed successfully:

        Document: {{ filename }}
        Status: {{ status }}
        Processing Score: {{ score }}/10
        Processed At: {{ processed_at }}

        {% if attachments %}
        Attached Files:
        {% for attachment in attachments %}
        - {{ attachment }}
        {% endfor %}
        {% endif %}

        Best regards,
        Document Processing System
        """
        )

    def prepare_email(self, document_data: dict) -> dict:
        """Prepare email content using Jinja2 template"""
        # Validate recipient
        recipient = "cloudwisedk@gmail.com"
        try:
            validate_email(recipient)
        except EmailNotValidError as e:
            raise HTTPException(status_code=500, detail=f"Invalid recipient email: {e}")

        # Render email body
        body = self.email_template.render(
            filename=document_data['filename'],
            status=document_data['status'],
            score=document_data['score'],
            processed_at=document_data['processed_at'],
            attachments=document_data.get('attachments', [])
        )

        return {
            "to": recipient,
            "subject": f"Document Processed: {document_data['filename']}",
            "body": body,
            "attachments": document_data.get('attachments', [])
        }


@app.post("/prepare_email")
async def prepare_email(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Endpoint: prepare and return email payload for a processed document"""
    # Fetch document and result
    document = db.query(Document).filter(Document.id == document_id).first()
    result = (
        db.query(ProcessingResult)
          .filter(ProcessingResult.document_id == document_id)
          .order_by(ProcessingResult.created_at.desc())
          .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if not result:
        raise HTTPException(status_code=404, detail="Processing result not found")

    # Prepare data for template
    document_data = {
        'filename': document.filename,
        'status': document.status,
        'score': result.overall_score * 10,  # scale to 0-10
        'processed_at': document.processed_at.strftime('%Y-%m-%d %H:%M:%S') if document.processed_at else None,
        'attachments': [document.file_path]
    }

    service = EmailService()
    email_payload = service.prepare_email(document_data)

    return email_payload