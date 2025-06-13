import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import re
from datetime import datetime
import email
from email import policy
import io


class DocumentPreprocessor:

    @staticmethod
    def extract_text_from_pdf(file_path):
        """Extract text from PDF using PyMuPDF and OCR fallback"""
        text = ""
        doc = fitz.open(file_path)

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()

            if page_text.strip():
                text += page_text
            else:
                # Use OCR for scanned PDFs
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                ocr_text = pytesseract.image_to_string(img)
                text += ocr_text

        doc.close()
        return text

    @staticmethod
    def extract_text_from_eml(file_path):
        """Extract text from EML files"""
        with open(file_path, 'rb') as f:
            msg = email.message_from_bytes(f.read(), policy=policy.default)

        text = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    text += part.get_content()
        else:
            if msg.get_content_type() == "text/plain":
                text = msg.get_content()

        return text

    @staticmethod
    def normalize_text(text):
        """Clean and normalize extracted text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Normalize dates
        date_pattern = r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})\b'
        text = re.sub(date_pattern, r'\1/\2/\3', text)

        # Normalize IDs (remove special characters)
        id_pattern = r'[^\w\s]'
        # Keep original text but create normalized version for processing

        return text.strip()

    @staticmethod
    def extract_entities(text):
        """Extract key entities like dates, IDs, amounts"""
        entities = {}

        # Extract dates
        date_pattern = r'\b(\d{1,2}\/\d{1,2}\/\d{2,4})\b'
        dates = re.findall(date_pattern, text)
        entities['dates'] = dates

        # Extract currency amounts
        amount_pattern = r'[\$€£]\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
        amounts = re.findall(amount_pattern, text)
        entities['amounts'] = amounts

        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        entities['emails'] = emails

        return entities