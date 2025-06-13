from fastapi import FastAPI, Depends, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.database import get_db
from services.preprocessing import DocumentPreprocessor
from app.models import ProcessingResult, Customer, Policy, Document, Invoice, Transaction

# Optional: imports for your scoring logic
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import fuzz
import numpy as np
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Analysis & Scoring Service")


class AnalyzeRequest(BaseModel):
    document_id: int
    text: str


class AnalyzeResponse(BaseModel):
    document_id: int
    scores: dict
    requires_manual_review: bool
    matched_records: dict


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db
        # Initialize any models/vectorizers here
        self.customer_vectorizer = TfidfVectorizer(max_features=1000)
        self.policy_classifier = None  # Placeholder for a trained classifier

    def customer_match_lookup(self, text: str) -> float:
        """Match customer information from database"""
        try:
            # Get all customers from database
            customers = self.db.query(Customer).all()

            if not customers:
                logger.warning("No customers found in database")
                return 0.0

            best_match_score = 0
            customer_indicators = self._extract_customer_info(text)

            # Also check for email addresses in text
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails_in_text = re.findall(email_pattern, text)

            for customer in customers:
                # Check name matching
                for indicator in customer_indicators:
                    name_score = fuzz.partial_ratio(indicator.lower(), customer.name.lower())
                    best_match_score = max(best_match_score, name_score)

                # Check email matching
                if customer.email:
                    for email in emails_in_text:
                        email_score = fuzz.ratio(email.lower(), customer.email.lower())
                        best_match_score = max(best_match_score, email_score)

                # Check phone matching if available
                if customer.phone:
                    phone_pattern = r'[\d\-\(\)\+\s]+'
                    phones_in_text = re.findall(phone_pattern, text)
                    for phone in phones_in_text:
                        # Clean phone numbers for comparison
                        clean_customer_phone = re.sub(r'[\D]', '', customer.phone)
                        clean_text_phone = re.sub(r'[\D]', '', phone)
                        if len(clean_text_phone) >= 7:  # Minimum phone length
                            phone_score = fuzz.ratio(clean_customer_phone, clean_text_phone)
                            best_match_score = max(best_match_score, phone_score)

            return best_match_score / 100.0

        except Exception as e:
            logger.error(f"Error in customer matching: {str(e)}")
            return 0.0

    def policy_match(self, text: str) -> float:
        """Match policy information from database"""
        try:
            # Get all policies from database
            policies = self.db.query(Policy).all()

            if not policies:
                logger.warning("No policies found in database")
                return 0.0

            best_match_score = 0

            # Extract potential policy numbers from text
            # Common policy number patterns (adjust based on your format)
            policy_patterns = [
                r'[A-Z]{2,3}\d{6,10}',  # e.g., POL123456789
                r'\d{8,12}',  # e.g., 123456789012
                r'[A-Z]\d{7,9}',  # e.g., P12345678
            ]

            potential_policy_numbers = []
            for pattern in policy_patterns:
                matches = re.findall(pattern, text)
                potential_policy_numbers.extend(matches)

            for policy in policies:
                # Direct policy number matching
                for potential_number in potential_policy_numbers:
                    score = fuzz.ratio(potential_number, policy.policy_number)
                    best_match_score = max(best_match_score, score)

                # Partial matching for policy numbers mentioned in text
                if policy.policy_number.lower() in text.lower():
                    best_match_score = max(best_match_score, 90)

            # Also check for policy-related keywords
            policy_keywords = ['policy', 'coverage', 'premium', 'claim', 'deductible', 'beneficiary']
            keyword_matches = sum(1 for kw in policy_keywords if kw.lower() in text.lower())
            keyword_score = min(keyword_matches / len(policy_keywords) * 50, 50)  # Max 50% from keywords

            return max(best_match_score / 100.0, keyword_score / 100.0)

        except Exception as e:
            logger.error(f"Error in policy matching: {str(e)}")
            return 0.0

    def invoice_reconciliation(self, text: str) -> float:
        """Reconcile invoice/financial data against database records"""
        try:
            # Extract financial entities
            entities = DocumentPreprocessor.extract_entities(text)
            score = 0.0
            max_score = 1.0

            # Get invoices and transactions from database
            invoices = self.db.query(Invoice).all()
            transactions = self.db.query(Transaction).all()

            # Extract amounts and dates from text
            amounts = entities.get('amounts', [])
            dates = entities.get('dates', [])

            # Extract potential invoice numbers from text
            invoice_number_patterns = [
                r'INV[-\s]?\d{4,10}',  # INV-123456 or INV 123456
                r'Invoice\s*#?\s*(\d{4,10})',  # Invoice #123456
                r'\b\d{6,10}\b',  # 6-10 digit numbers
                r'[A-Z]{2,3}\d{6,8}'  # ABC123456
            ]

            potential_invoice_numbers = []
            for pattern in invoice_number_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                potential_invoice_numbers.extend(matches)

            # Score based on invoice matching
            invoice_match_score = 0.0
            if invoices:
                best_invoice_match = 0

                for invoice in invoices:
                    # Direct invoice number matching
                    for potential_number in potential_invoice_numbers:
                        match_score = fuzz.ratio(str(potential_number), invoice.invoice_number)
                        best_invoice_match = max(best_invoice_match, match_score)

                    # Amount matching
                    for amount in amounts:
                        try:
                            # Clean amount string and convert to float
                            clean_amount = re.sub(r'[^\d.]', '', str(amount))
                            if clean_amount:
                                text_amount = float(clean_amount)
                                if abs(text_amount - invoice.amount) < 0.01:  # Exact match
                                    best_invoice_match = max(best_invoice_match, 95)
                                elif abs(text_amount - invoice.amount) / invoice.amount < 0.05:  # 5% tolerance
                                    best_invoice_match = max(best_invoice_match, 80)
                        except (ValueError, ZeroDivisionError):
                            continue

                invoice_match_score = best_invoice_match / 100.0
                score += invoice_match_score * 0.4  # 40% weight for invoice matching

            # Score based on transaction matching
            transaction_match_score = 0.0
            if transactions:
                best_transaction_match = 0

                for transaction in transactions:
                    # Transaction ID matching
                    if transaction.transaction_id.lower() in text.lower():
                        best_transaction_match = max(best_transaction_match, 90)

                    # Reference number matching
                    if transaction.reference_number and transaction.reference_number.lower() in text.lower():
                        best_transaction_match = max(best_transaction_match, 85)

                    # Amount matching
                    for amount in amounts:
                        try:
                            clean_amount = re.sub(r'[^\d.]', '', str(amount))
                            if clean_amount:
                                text_amount = float(clean_amount)
                                if abs(text_amount - transaction.amount) < 0.01:
                                    best_transaction_match = max(best_transaction_match, 90)
                                elif abs(text_amount - transaction.amount) / abs(transaction.amount) < 0.05:
                                    best_transaction_match = max(best_transaction_match, 75)
                        except (ValueError, ZeroDivisionError):
                            continue

                transaction_match_score = best_transaction_match / 100.0
                score += transaction_match_score * 0.3  # 30% weight for transaction matching

            # Basic document structure scoring
            structure_score = 0.0

            # Check for amounts
            if amounts:
                structure_score += 0.1
                if len(amounts) > 1:
                    structure_score += 0.05  # Multiple amounts suggest detailed invoice

            # Check for invoice-specific keywords
            invoice_keywords = [
                'invoice', 'receipt', 'payment', 'bill', 'statement',
                'total', 'subtotal', 'tax', 'due', 'balance', 'amount due',
                'paid', 'transaction', 'reference'
            ]
            keyword_matches = sum(1 for kw in invoice_keywords if kw.lower() in text.lower())
            structure_score += min(keyword_matches / len(invoice_keywords), 0.15)

            # Check for dates
            if dates:
                structure_score += 0.05

            score += structure_score

            # Bonus for having both invoice and transaction matches
            if invoice_match_score > 0.5 and transaction_match_score > 0.5:
                score += 0.1  # 10% bonus for cross-validation

            return min(score, max_score)

        except Exception as e:
            logger.error(f"Error in invoice reconciliation: {str(e)}")
            return 0.0

    def calculate_data_quality_score(self, text: str, entities: dict) -> float:
        """Calculate data quality score based on extracted entities and text analysis"""
        try:
            score = 0.0
            max_score = 10.0

            # Check for key entities
            if entities.get('dates'):
                score += 2.0
            if entities.get('amounts'):
                score += 2.0
            if entities.get('emails'):
                score += 1.5

            # Text length and structure
            if len(text) > 100:
                score += 1.5
            if len(text) > 500:
                score += 1.0

            # Check for structured content
            if any(char in text for char in ['\n', '\t', '|']):
                score += 1.0  # Structured format

            # Check for common document elements
            document_indicators = ['date:', 'amount:', 'total:', 'from:', 'to:', 'subject:']
            indicator_matches = sum(1 for indicator in document_indicators if indicator.lower() in text.lower())
            score += min(indicator_matches * 0.5, 1.0)

            return min(score / max_score, 1.0)

        except Exception as e:
            logger.error(f"Error calculating data quality score: {str(e)}")
            return 0.0

    def _extract_customer_info(self, text: str) -> list[str]:
        """Extract potential customer names and identifiers from text"""
        names = []
        words = text.split()

        # Look for titles followed by names
        for i, word in enumerate(words[:-1]):
            if word.lower() in ['mr', 'mrs', 'ms', 'dr', 'mr.', 'mrs.', 'ms.', 'dr.','name']:
                if i + 1 < len(words):
                    names.append(f"{word} {words[i + 1]}")
                    if i + 2 < len(words) and words[i + 2].replace(',', '').isalpha():
                        names.append(f"{word} {words[i + 1]} {words[i + 2]}")

        # Look for "Dear [Name]" patterns
        dear_pattern = r'Dear\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        dear_matches = re.findall(dear_pattern, text)
        names.extend(dear_matches)

        # Look for "Name:" patterns
        name_pattern = r'Name:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        name_matches = re.findall(name_pattern, text)
        names.extend(name_matches)

        return names

    def get_matched_records(self, text: str) -> dict:
        """Get details of matched records for audit trail"""
        try:
            matched_records = {
                'customers': [],
                'policies': [],
                'invoices': [],
                'transactions': []
            }

            # Get matched customers
            customers = self.db.query(Customer).all()
            customer_indicators = self._extract_customer_info(text)
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails_in_text = re.findall(email_pattern, text)

            for customer in customers:
                match_score = 0
                match_reason = []

                # Check name matching
                for indicator in customer_indicators:
                    name_score = fuzz.partial_ratio(indicator.lower(), customer.name.lower())
                    if name_score > 70:
                        match_score = max(match_score, name_score)
                        match_reason.append(f"Name match: {indicator}")

                # Check email matching
                if customer.email:
                    for email in emails_in_text:
                        email_score = fuzz.ratio(email.lower(), customer.email.lower())
                        if email_score > 80:
                            match_score = max(match_score, email_score)
                            match_reason.append(f"Email match: {email}")

                if match_score > 70:
                    matched_records['customers'].append({
                        'id': customer.id,
                        'name': customer.name,
                        'email': customer.email,
                        'match_score': match_score,
                        'match_reason': match_reason
                    })

            # Get matched policies
            policies = self.db.query(Policy).all()
            policy_patterns = [r'[A-Z]{2,3}\d{6,10}', r'\d{8,12}', r'[A-Z]\d{7,9}']
            potential_policy_numbers = []
            for pattern in policy_patterns:
                matches = re.findall(pattern, text)
                potential_policy_numbers.extend(matches)

            for policy in policies:
                match_score = 0
                match_reason = []

                for potential_number in potential_policy_numbers:
                    score = fuzz.ratio(potential_number, policy.policy_number)
                    if score > 70:
                        match_score = max(match_score, score)
                        match_reason.append(f"Policy number match: {potential_number}")

                if policy.policy_number.lower() in text.lower():
                    match_score = max(match_score, 90)
                    match_reason.append(f"Direct policy mention: {policy.policy_number}")

                if match_score > 70:
                    matched_records['policies'].append({
                        'id': policy.id,
                        'policy_number': policy.policy_number,
                        'policy_type': policy.policy_type,
                        'match_score': match_score,
                        'match_reason': match_reason
                    })

            # Get matched invoices
            invoices = self.db.query(Invoice).all()
            entities = DocumentPreprocessor.extract_entities(text)
            amounts = entities.get('amounts', [])

            for invoice in invoices:
                match_score = 0
                match_reason = []

                # Check invoice number
                if invoice.invoice_number.lower() in text.lower():
                    match_score = max(match_score, 95)
                    match_reason.append(f"Invoice number match: {invoice.invoice_number}")

                # Check amount matching
                for amount in amounts:
                    try:
                        clean_amount = re.sub(r'[^\d.]', '', str(amount))
                        if clean_amount:
                            text_amount = float(clean_amount)
                            if abs(text_amount - invoice.amount) < 0.01:
                                match_score = max(match_score, 95)
                                match_reason.append(f"Exact amount match: ${invoice.amount}")
                            elif abs(text_amount - invoice.amount) / invoice.amount < 0.05:
                                match_score = max(match_score, 80)
                                match_reason.append(f"Close amount match: ${invoice.amount}")
                    except (ValueError, ZeroDivisionError):
                        continue

                if match_score > 70:
                    matched_records['invoices'].append({
                        'id': invoice.id,
                        'invoice_number': invoice.invoice_number,
                        'amount': invoice.amount,
                        'customer_id': invoice.customer_id,
                        'match_score': match_score,
                        'match_reason': match_reason
                    })

            # Get matched transactions
            transactions = self.db.query(Transaction).all()

            for transaction in transactions:
                match_score = 0
                match_reason = []

                # Check transaction ID
                if transaction.transaction_id.lower() in text.lower():
                    match_score = max(match_score, 90)
                    match_reason.append(f"Transaction ID match: {transaction.transaction_id}")

                # Check reference number
                if transaction.reference_number and transaction.reference_number.lower() in text.lower():
                    match_score = max(match_score, 85)
                    match_reason.append(f"Reference match: {transaction.reference_number}")

                # Check amount matching
                for amount in amounts:
                    try:
                        clean_amount = re.sub(r'[^\d.]', '', str(amount))
                        if clean_amount:
                            text_amount = float(clean_amount)
                            if abs(text_amount - transaction.amount) < 0.01:
                                match_score = max(match_score, 90)
                                match_reason.append(f"Exact amount match: ${transaction.amount}")
                    except (ValueError, ZeroDivisionError):
                        continue

                if match_score > 70:
                    matched_records['transactions'].append({
                        'id': transaction.id,
                        'transaction_id': transaction.transaction_id,
                        'amount': transaction.amount,
                        'transaction_type': transaction.transaction_type,
                        'match_score': match_score,
                        'match_reason': match_reason
                    })

            return matched_records

        except Exception as e:
            logger.error(f"Error getting matched records: {str(e)}")
            return {'customers': [], 'policies': [], 'invoices': [], 'transactions': []}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_document(
        req: AnalyzeRequest = Body(...),
        db: Session = Depends(get_db)
):
    try:
        logger.info(f"Starting analysis for document {req.document_id}")

        # Initialize service with database session
        service = AnalysisService(db)
        text = req.text
        document_id = req.document_id

        # Verify document exists
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Extract entities first
        entities = DocumentPreprocessor.extract_entities(text)

        # Calculate scores using database data
        customer_score = service.customer_match_lookup(text)
        policy_score = service.policy_match(text)
        reconciliation_score = service.invoice_reconciliation(text)
        quality_score = service.calculate_data_quality_score(text, entities)

        # Calculate overall score with weighted average
        weights = {
            'customer': 0.3,
            'policy': 0.3,
            'reconciliation': 0.2,
            'quality': 0.2
        }

        overall = (
                customer_score * weights['customer'] +
                policy_score * weights['policy'] +
                reconciliation_score * weights['reconciliation'] +
                quality_score * weights['quality']
        )

        # Determine if manual review is required
        manual_flag = overall < 0.6 or any([
            customer_score < 0.3,
            policy_score < 0.3,
            quality_score < 0.4
        ])

        # Persist results
        result = ProcessingResult(
            document_id=document_id,
            extracted_text=text,
            customer_match_score=customer_score,
            policy_match_score=policy_score,
            invoice_reconciliation_score=reconciliation_score,
            data_quality_score=quality_score,
            overall_score=overall,
            requires_manual_review=manual_flag,
            created_at=datetime.utcnow()
        )
        db.add(result)
        db.commit()

        # Get matched records for audit trail
        matched_records = service.get_matched_records(text)

        logger.info(f"Analysis completed for document {document_id}")

        return AnalyzeResponse(
            document_id=document_id,
            scores={
                "customer_match": round(customer_score, 3),
                "policy_match": round(policy_score, 3),
                "invoice_reconciliation": round(reconciliation_score, 3),
                "data_quality": round(quality_score, 3),
                "overall": round(overall, 3)
            },
            requires_manual_review=manual_flag,
            matched_records=matched_records
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing document {req.document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Analysis & Scoring"}