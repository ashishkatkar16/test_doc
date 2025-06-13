from fastapi import FastAPI, HTTPException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import logging
import requests

app = FastAPI(title="RPA Robot Service")

logger = logging.getLogger(__name__)


class RPAService:

    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")

    def send_email(self, email_data):
        """Send email via SMTP"""

        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = email_data['to']
            msg['Subject'] = email_data['subject']

            # Add body
            msg.attach(MIMEText(email_data['body'], 'plain'))

            # Add attachments
            for file_path in email_data.get('attachments', []):
                if os.path.exists(file_path):
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())

                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {os.path.basename(file_path)}'
                    )
                    msg.attach(part)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)

            text = msg.as_string()
            server.sendmail(self.smtp_username, email_data['to'], text)
            server.quit()

            logger.info(f"Email sent successfully to {email_data['to']}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False


@app.post("/send_email")
async def send_email(document_id: int):
    """Send email for processed document"""

    # Get email data from email preparation service
    response = requests.post(
        "http://localhost:8002/prepare_email",
        params={"document_id": document_id}
    )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to prepare email")

    email_data = response.json()

    service = RPAService()
    success = service.send_email(email_data)

    try:
        resp = requests.post(
            "http://localhost:8004/update_dashboard",
            json={"document_id": document_id, "status": "email_sent"},
            timeout=5
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Could not update dashboard (document={document_id}): {e}")

    return {"status": success, "document_id": document_id}