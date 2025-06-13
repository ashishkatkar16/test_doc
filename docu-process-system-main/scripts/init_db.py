#!/usr/bin/env python3
"""
Database initialization script for Document Processing System
"""
import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.database import create_tables, engine, SessionLocal
from app.models import Customer, Policy, DocumentType, Document, ProcessingResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test if database connection is working"""
    try:
        with engine.connect() as connection:
            # Use text() for raw SQL queries in SQLAlchemy 2.0+
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def initialize_database():
    """Initialize database tables and basic data"""
    try:
        logger.info("Creating database tables...")
        create_tables()
        logger.info("✅ Database tables created successfully")

        # Optional: Add some initial data
        with SessionLocal() as session:
            # Check if document types already exist
            existing_types = session.query(DocumentType).count()
            if existing_types == 0:
                logger.info("Adding initial document types...")
                doc_types = [
                    DocumentType(name="Invoice", description="Customer invoices and billing documents"),
                    DocumentType(name="Policy", description="Insurance policy documents"),
                    DocumentType(name="Claim", description="Insurance claim documents"),
                    DocumentType(name="Contract", description="Service contracts and agreements")
                ]
                session.add_all(doc_types)
                session.commit()
                logger.info("✅ Initial document types added")
            else:
                logger.info("Document types already exist, skipping...")

        return True
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

def main():
    """Main initialization function"""
    print("=" * 50)
    print("Document Processing System - Database Initialization")
    print("=" * 50)

    # Test database connection
    if not test_database_connection():
        print("❌ Database connection failed. Please check your configuration.")
        return False

    # Initialize database
    if not initialize_database():
        print("❌ Database initialization failed.")
        return False

    print("✅ Database initialization completed successfully!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)