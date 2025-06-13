from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean
from datetime import datetime
from .database import Base  # Import Base from database.py


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)


class ProcessingResult(Base):
    __tablename__ = "processing_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False)
    extracted_text = Column(Text)
    customer_match_score = Column(Float)
    policy_match_score = Column(Float)
    invoice_reconciliation_score = Column(Float)
    data_quality_score = Column(Float)
    overall_score = Column(Float)
    requires_manual_review = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# If you need these models, add them here:
class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentType(Base):
    __tablename__ = "document_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    policy_number = Column(String, unique=True, nullable=False)
    customer_id = Column(Integer, nullable=True)
    policy_type = Column(String)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, nullable=False)
    customer_id = Column(Integer, nullable=True)
    policy_id = Column(Integer, nullable=True)
    amount = Column(Float, nullable=False)
    invoice_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="pending")  # pending, paid, overdue, cancelled
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, nullable=False)
    invoice_id = Column(Integer, nullable=True)
    customer_id = Column(Integer, nullable=True)
    amount = Column(Float, nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    transaction_type = Column(String)  # payment, refund, adjustment
    payment_method = Column(String)    # credit_card, bank_transfer, check, etc.
    status = Column(String, default="completed")
    reference_number = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)