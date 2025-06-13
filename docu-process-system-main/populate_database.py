#!/usr/bin/env python3
"""
Database Population Script
Run this script to populate your database with sample data for testing the Analysis service.

Usage:
    python populate_database.py
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Add the parent directory to the path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, create_tables
from app.models import Customer, Policy, Invoice, Transaction, Document, ProcessingResult


def populate_customers(db):
    """Populate customers table with sample data"""
    customers_data = [
        {
            "name": "John Doe",
            "email": "john.doe@email.com",
            "phone": "+1-555-0123"
        },
        {
            "name": "Jane Smith",
            "email": "jane.smith@email.com",
            "phone": "+1-555-0456"
        },
        {
            "name": "Robert Johnson",
            "email": "robert.johnson@email.com",
            "phone": "+1-555-0789"
        },
        {
            "name": "Emily Davis",
            "email": "emily.davis@email.com",
            "phone": "+1-555-0321"
        },
        {
            "name": "Michael Brown",
            "email": "michael.brown@email.com",
            "phone": "+1-555-0654"
        },
        {
            "name": "Sarah Wilson",
            "email": "sarah.wilson@email.com",
            "phone": "+1-555-0987"
        },
        {
            "name": "David Miller",
            "email": "david.miller@email.com",
            "phone": "+1-555-0147"
        },
        {
            "name": "Lisa Anderson",
            "email": "lisa.anderson@email.com",
            "phone": "+1-555-0258"
        },
        {
            "name": "James Taylor",
            "email": "james.taylor@email.com",
            "phone": "+1-555-0369"
        },
        {
            "name": "Maria Garcia",
            "email": "maria.garcia@email.com",
            "phone": "+1-555-0741"
        }
    ]

    customers = []
    for customer_data in customers_data:
        customer = Customer(**customer_data)
        customers.append(customer)
        db.add(customer)

    db.commit()
    print(f"Added {len(customers)} customers")
    return customers


def populate_policies(db, customers):
    """Populate policies table with sample data"""
    policy_types = ["Auto", "Home", "Life", "Health", "Business", "Travel"]
    statuses = ["active", "expired", "cancelled", "pending"]

    policies = []
    for i, customer in enumerate(customers):
        # Each customer gets 1-3 policies
        num_policies = random.randint(1, 3)

        for j in range(num_policies):
            policy_number = f"POL{customer.id:03d}{j + 1:02d}{random.randint(1000, 9999)}"
            policy = Policy(
                policy_number=policy_number,
                customer_id=customer.id,
                policy_type=random.choice(policy_types),
                status=random.choice(statuses) if random.random() > 0.8 else "active"  # 80% active
            )
            policies.append(policy)
            db.add(policy)

    db.commit()
    print(f"Added {len(policies)} policies")
    return policies


def populate_invoices(db, customers, policies):
    """Populate invoices table with sample data"""
    invoice_statuses = ["pending", "paid", "overdue", "cancelled"]

    invoices = []
    for i, customer in enumerate(customers):
        # Each customer gets 2-5 invoices
        num_invoices = random.randint(2, 5)

        for j in range(num_invoices):
            invoice_date = datetime.now() - timedelta(days=random.randint(1, 365))
            due_date = invoice_date + timedelta(days=random.randint(15, 45))
            amount = round(random.uniform(100.0, 2500.0), 2)

            # Find a policy for this customer
            customer_policies = [p for p in policies if p.customer_id == customer.id]
            policy_id = random.choice(customer_policies).id if customer_policies else None

            invoice = Invoice(
                invoice_number=f"INV-{customer.id:03d}-{j + 1:03d}-{random.randint(1000, 9999)}",
                customer_id=customer.id,
                policy_id=policy_id,
                amount=amount,
                invoice_date=invoice_date,
                due_date=due_date,
                status=random.choice(invoice_statuses),
                description=f"Premium payment for {random.choice(['Auto', 'Home', 'Life', 'Health'])} insurance policy"
            )
            invoices.append(invoice)
            db.add(invoice)

    db.commit()
    print(f"Added {len(invoices)} invoices")
    return invoices


def populate_transactions(db, customers, invoices):
    """Populate transactions table with sample data"""
    transaction_types = ["payment", "refund", "adjustment"]
    payment_methods = ["credit_card", "bank_transfer", "check", "cash", "online"]
    transaction_statuses = ["completed", "pending", "failed", "cancelled"]

    transactions = []
    for invoice in invoices:
        # 70% of invoices have at least one transaction
        if random.random() > 0.3:
            # Some invoices might have multiple transactions (partial payments, refunds, etc.)
            num_transactions = random.choices([1, 2, 3], weights=[70, 25, 5])[0]

            remaining_amount = invoice.amount
            for j in range(num_transactions):
                transaction_date = invoice.invoice_date + timedelta(days=random.randint(1, 30))

                if j == 0:  # First transaction
                    if num_transactions == 1:
                        # Full payment
                        amount = invoice.amount
                        transaction_type = "payment"
                    else:
                        # Partial payment
                        amount = round(remaining_amount * random.uniform(0.3, 0.8), 2)
                        transaction_type = "payment"
                else:
                    # Subsequent transactions
                    if random.random() > 0.8:  # 20% chance of refund/adjustment
                        transaction_type = random.choice(["refund", "adjustment"])
                        amount = round(random.uniform(10.0, min(100.0, remaining_amount)), 2)
                    else:
                        transaction_type = "payment"
                        amount = min(remaining_amount, round(random.uniform(50.0, remaining_amount), 2))

                remaining_amount -= amount if transaction_type == "payment" else -amount

                transaction = Transaction(
                    transaction_id=f"TXN{invoice.customer_id:03d}{j + 1:02d}{random.randint(100000, 999999)}",
                    invoice_id=invoice.id,
                    customer_id=invoice.customer_id,
                    amount=amount,
                    transaction_date=transaction_date,
                    transaction_type=transaction_type,
                    payment_method=random.choice(payment_methods),
                    status=random.choice(transaction_statuses) if random.random() > 0.9 else "completed",
                    reference_number=f"REF{random.randint(1000000, 9999999)}"
                )
                transactions.append(transaction)
                db.add(transaction)

    db.commit()
    print(f"Added {len(transactions)} transactions")
    return transactions


def populate_sample_documents(db, customers):
    """Populate documents table with sample data"""
    document_types = [
        "invoice.pdf", "receipt.pdf", "policy_document.pdf",
        "claim_form.pdf", "payment_confirmation.pdf"
    ]

    documents = []
    for i, customer in enumerate(customers):
        # Each customer gets 1-3 documents
        num_docs = random.randint(1, 3)

        for j in range(num_docs):
            filename = f"customer_{customer.id}_{random.choice(document_types)}"
            document = Document(
                filename=filename,
                file_path=f"/uploads/{filename}",
                status=random.choice(["pending", "processed", "failed"]),
                created_at=datetime.now() - timedelta(days=random.randint(1, 30))
            )
            documents.append(document)
            db.add(document)

    db.commit()
    print(f"Added {len(documents)} documents")
    return documents


def create_sample_text_data(customers, policies, invoices, transactions):
    """Create sample text data that would be extracted from documents"""

    sample_texts = []

    # Sample invoice text
    customer = customers[0]  # John Doe
    customer_invoices = [inv for inv in invoices if inv.customer_id == customer.id]
    if customer_invoices:
        invoice = customer_invoices[0]
        invoice_text = f"""
        INVOICE

        Invoice Number: {invoice.invoice_number}
        Date: {invoice.invoice_date.strftime('%Y-%m-%d')}
        Due Date: {invoice.due_date.strftime('%Y-%m-%d')}

        Bill To:
        {customer.name}
        Email: {customer.email}
        Phone: {customer.phone}

        Description: {invoice.description}
        Amount: ${invoice.amount:.2f}
        Total Due: ${invoice.amount:.2f}

        Please remit payment by the due date.
        """
        sample_texts.append(("Invoice Document", invoice_text))

    # Sample payment confirmation
    customer = customers[1]  # Jane Smith
    customer_transactions = [txn for txn in transactions if txn.customer_id == customer.id]
    if customer_transactions:
        transaction = customer_transactions[0]
        payment_text = f"""
        PAYMENT CONFIRMATION

        Transaction ID: {transaction.transaction_id}
        Reference Number: {transaction.reference_number}
        Date: {transaction.transaction_date.strftime('%Y-%m-%d')}

        Customer: {customer.name}
        Email: {customer.email}

        Payment Method: {transaction.payment_method.replace('_', ' ').title()}
        Amount Paid: ${transaction.amount:.2f}
        Status: {transaction.status.title()}

        Thank you for your payment.
        """
        sample_texts.append(("Payment Confirmation", payment_text))

    # Sample policy document
    customer = customers[2]  # Robert Johnson
    customer_policies = [pol for pol in policies if pol.customer_id == customer.id]
    if customer_policies:
        policy = customer_policies[0]
        policy_text = f"""
        INSURANCE POLICY DOCUMENT

        Policy Number: {policy.policy_number}
        Policy Type: {policy.policy_type}
        Status: {policy.status.title()}

        Policyholder Information:
        Name: {customer.name}
        Email: {customer.email}
        Phone: {customer.phone}

        This policy provides {policy.policy_type.lower()} insurance coverage
        as outlined in the terms and conditions.

        For questions, please contact our customer service department.
        """
        sample_texts.append(("Policy Document", policy_text))

    return sample_texts


def main():
    """Main function to populate the database"""
    print("Starting database population...")

    # Create tables if they don't exist
    create_tables()

    # Create database session
    db = SessionLocal()

    try:
        # Check if data already exists
        existing_customers = db.query(Customer).count()
        if existing_customers > 0:
            print(f"Database already has {existing_customers} customers.")
            response = input("Do you want to clear existing data and repopulate? (y/N): ")
            if response.lower() != 'y':
                print("Exiting without changes.")
                return

            # Clear existing data
            print("Clearing existing data...")
            db.query(ProcessingResult).delete()
            db.query(Transaction).delete()
            db.query(Invoice).delete()
            db.query(Document).delete()
            db.query(Policy).delete()
            db.query(Customer).delete()
            db.commit()
            print("Existing data cleared.")

        # Populate tables
        print("\nPopulating database tables...")
        customers = populate_customers(db)
        policies = populate_policies(db, customers)
        invoices = populate_invoices(db, customers, policies)
        transactions = populate_transactions(db, customers, invoices)
        documents = populate_sample_documents(db, customers)

        print(f"\nDatabase populated successfully!")
        print(f"- {len(customers)} customers")
        print(f"- {len(policies)} policies")
        print(f"- {len(invoices)} invoices")
        print(f"- {len(transactions)} transactions")
        print(f"- {len(documents)} documents")

        # Create sample text data for testing
        sample_texts = create_sample_text_data(customers, policies, invoices, transactions)

        print(f"\nSample text data for testing the Analysis service:")
        print("=" * 60)

        for title, text in sample_texts:
            print(f"\n{title}:")
            print("-" * 40)
            print(text.strip())
            print("-" * 40)

        print(f"\nYou can use these sample texts to test your /analyze endpoint!")
        print("Example API call:")
        print("""
        POST /analyze
        {
            "document_id": 1,
            "text": "<paste one of the sample texts above>"
        }
        """)

    except Exception as e:
        print(f"Error populating database: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()