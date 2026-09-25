"""Seed the database with demo users and sample documents."""

import logging

from backend.auth import hash_password
from backend.database import Document, SessionLocal, User, init_db
from backend.rag.document_loader import load_and_index_text

logger = logging.getLogger(__name__)


def seed_users(db) -> None:
    """Create demo admin, staff, and user accounts."""
    if db.query(User).count() > 0:
        logger.info("Users already seeded, skipping.")
        return

    users = [
        # Admin
        User(
            username="admin",
            email="admin@company.com",
            hashed_password=hash_password("admin123"),
            full_name="System Administrator",
            role="admin",
            department="IT",
            phone="+1-555-0100",
        ),
        # Staff members
        User(
            username="staff_sarah",
            email="sarah@company.com",
            hashed_password=hash_password("staff123"),
            full_name="Sarah Johnson",
            role="staff",
            department="Customer Support",
            phone="+1-555-0201",
        ),
        User(
            username="staff_mike",
            email="mike@company.com",
            hashed_password=hash_password("staff123"),
            full_name="Mike Chen",
            role="staff",
            department="Sales",
            phone="+1-555-0202",
        ),
        # Regular users
        User(
            username="user_alice",
            email="alice@customer.com",
            hashed_password=hash_password("user123"),
            full_name="Alice Williams",
            role="user",
            department="Engineering",
            phone="+1-555-0301",
        ),
        User(
            username="user_bob",
            email="bob@customer.com",
            hashed_password=hash_password("user123"),
            full_name="Bob Martinez",
            role="user",
            department="Marketing",
            phone="+1-555-0302",
        ),
        User(
            username="user_carol",
            email="carol@customer.com",
            hashed_password=hash_password("user123"),
            full_name="Carol Davis",
            role="user",
            department="Finance",
            phone="+1-555-0303",
        ),
    ]

    for u in users:
        db.add(u)
    db.commit()

    # Assign staff to users
    alice = db.query(User).filter(User.username == "user_alice").first()
    bob = db.query(User).filter(User.username == "user_bob").first()
    carol = db.query(User).filter(User.username == "user_carol").first()
    sarah = db.query(User).filter(User.username == "staff_sarah").first()
    mike = db.query(User).filter(User.username == "staff_mike").first()

    alice.assigned_staff_id = sarah.id  # Sarah manages Alice
    bob.assigned_staff_id = sarah.id    # Sarah manages Bob
    carol.assigned_staff_id = mike.id   # Mike manages Carol
    db.commit()

    logger.info(f"Seeded {len(users)} users with staff assignments.")


def seed_documents(db) -> None:
    """Create sample knowledge base documents and index them for RAG."""
    if db.query(Document).count() > 0:
        logger.info("Documents already seeded, skipping.")
        return

    documents = [
        {
            "title": "Company Leave Policy",
            "content": (
                "Company Leave Policy\n\n"
                "1. Annual Leave: All full-time employees are entitled to 20 days of paid "
                "annual leave per calendar year. Leave must be requested at least 2 weeks "
                "in advance through the HR portal.\n\n"
                "2. Sick Leave: Employees receive 10 days of paid sick leave per year. "
                "A medical certificate is required for absences exceeding 3 consecutive days.\n\n"
                "3. Parental Leave: New parents are entitled to 12 weeks of paid parental "
                "leave. This applies to both primary and secondary caregivers.\n\n"
                "4. Emergency Leave: Up to 5 days of emergency leave may be granted for "
                "family emergencies, subject to manager approval.\n\n"
                "5. Public Holidays: The company observes 11 public holidays per year. "
                "Employees required to work on public holidays receive double pay.\n\n"
                "6. Carryover: Unused annual leave up to 5 days may be carried over to "
                "the next year. Leave beyond this is forfeited."
            ),
            "category": "policy",
            "access_level": "all",
        },
        {
            "title": "IT Security Guidelines",
            "content": (
                "IT Security Guidelines\n\n"
                "1. Passwords: All passwords must be at least 12 characters, include "
                "uppercase, lowercase, numbers, and symbols. Change passwords every 90 days.\n\n"
                "2. Two-Factor Authentication (2FA): 2FA is mandatory for all systems "
                "containing customer data or financial information.\n\n"
                "3. VPN: Remote workers must connect through the company VPN. Never "
                "access company systems from public WiFi without VPN.\n\n"
                "4. Email Security: Do not open attachments from unknown senders. Report "
                "suspicious emails to security@company.com immediately.\n\n"
                "5. Data Classification: Data is classified as Public, Internal, "
                "Confidential, or Restricted. Handle each according to its classification.\n\n"
                "6. Device Policy: Company laptops must have full-disk encryption enabled. "
                "Personal devices cannot access Confidential or Restricted data.\n\n"
                "7. Incident Response: Report security incidents within 1 hour of discovery "
                "to the IT Security team. Do not attempt to investigate on your own."
            ),
            "category": "technical",
            "access_level": "all",
        },
        {
            "title": "Staff Operations Manual",
            "content": (
                "Staff Operations Manual\n\n"
                "1. Customer Handling: Always greet customers professionally. Resolve "
                "issues within 24 hours where possible. Escalate complex cases to team leads.\n\n"
                "2. Shift Management: Staff shifts are posted weekly. Swap requests must "
                "be submitted 48 hours in advance. No-show penalties apply after 3 incidents.\n\n"
                "3. Performance Reviews: Conducted quarterly. KPIs include customer "
                "satisfaction score, resolution time, and ticket volume.\n\n"
                "4. Training: All new staff complete a 2-week onboarding program. "
                "Monthly skill workshops are mandatory.\n\n"
                "5. Escalation Matrix:\n"
                "   - Level 1: Front-line staff → common issues\n"
                "   - Level 2: Senior staff → complex technical issues\n"
                "   - Level 3: Team leads → billing disputes and complaints\n"
                "   - Level 4: Management → legal and compliance issues\n\n"
                "6. Tools: Staff use CRM for ticket tracking, Slack for internal "
                "communication, and the Knowledge Base for reference."
            ),
            "category": "policy",
            "access_level": "staff",
        },
        {
            "title": "Admin System Architecture",
            "content": (
                "Admin System Architecture (CONFIDENTIAL)\n\n"
                "1. Infrastructure: The system runs on AWS with multi-AZ deployment. "
                "Primary region is us-east-1, failover in us-west-2.\n\n"
                "2. Database: PostgreSQL 15 on RDS with read replicas. Daily automated "
                "backups retained for 30 days. Point-in-time recovery enabled.\n\n"
                "3. Authentication: OAuth 2.0 with JWT tokens. Admin tokens expire "
                "after 1 hour. API rate limiting: 1000 requests/minute per user.\n\n"
                "4. Monitoring: Datadog for application metrics, PagerDuty for alerting. "
                "Critical alerts page the on-call engineer within 5 minutes.\n\n"
                "5. Deployment: CI/CD via GitHub Actions. Blue-green deployments with "
                "automatic rollback on >5% error rate.\n\n"
                "6. Access Control: Admin panel accessible only from corporate VPN. "
                "All admin actions are logged with user ID and timestamp.\n\n"
                "7. Encryption: AES-256 for data at rest, TLS 1.3 for data in transit. "
                "KMS for key management with annual key rotation."
            ),
            "category": "technical",
            "access_level": "admin",
        },
        {
            "title": "Employee Handbook",
            "content": (
                "Employee Handbook\n\n"
                "Welcome to the Company! This handbook covers everything you need to know.\n\n"
                "1. Working Hours: Standard hours are 9:00 AM to 5:30 PM, Monday through "
                "Friday. Flexible scheduling is available with manager approval.\n\n"
                "2. Dress Code: Business casual for office days. Smart casual for client "
                "meetings. Casual Fridays are observed.\n\n"
                "3. Remote Work: Employees may work remotely up to 3 days per week after "
                "completing their probation period (3 months).\n\n"
                "4. Benefits:\n"
                "   - Health insurance (medical, dental, vision)\n"
                "   - 401(k) with 4% company match\n"
                "   - Annual education allowance of $2,000\n"
                "   - Gym membership reimbursement up to $50/month\n"
                "   - Employee assistance program (EAP)\n\n"
                "5. Code of Conduct: Treat all colleagues with respect. Harassment and "
                "discrimination of any kind are strictly prohibited and grounds for "
                "immediate termination.\n\n"
                "6. Expense Policy: Business expenses must be submitted within 30 days "
                "with receipts. Pre-approval required for expenses over $500."
            ),
            "category": "general",
            "access_level": "all",
        },
    ]

    for doc_data in documents:
        doc = Document(
            title=doc_data["title"],
            filename=f"{doc_data['title'].replace(' ', '_').lower()}.txt",
            content=doc_data["content"],
            category=doc_data["category"],
            access_level=doc_data["access_level"],
        )
        db.add(doc)
    db.commit()

    # Index documents for RAG
    for doc_data in documents:
        try:
            load_and_index_text(
                title=doc_data["title"],
                content=doc_data["content"],
                access_level=doc_data["access_level"],
                category=doc_data["category"],
            )
        except Exception as e:
            logger.warning(f"Failed to index '{doc_data['title']}': {e}")

    logger.info(f"Seeded {len(documents)} documents.")


def seed_ecommerce(db) -> None:
    """Create dummy e-commerce products and orders."""
    from backend.database import Product, Order
    
    if db.query(Product).count() > 0:
        logger.info("E-commerce data already seeded, skipping.")
        return

    products = [
        Product(name="Quantum Laptop", description="High performance AI laptop", price=1999.99, stock=50, category="electronics"),
        Product(name="Ergonomic Keyboard", description="Mechanical split keyboard", price=149.50, stock=200, category="accessories"),
        Product(name="Wireless Mouse", description="Silent click ergonomic mouse", price=59.99, stock=500, category="accessories"),
        Product(name="AI Developer Monitor", description="4K ultrawide monitor", price=699.00, stock=30, category="electronics"),
    ]
    
    for p in products:
        db.add(p)
    db.commit()

    from datetime import datetime, timedelta, timezone
    
    # Add some dummy orders for users
    alice = db.query(User).filter(User.username == "user_alice").first()
    bob = db.query(User).filter(User.username == "user_bob").first()
    
    # Refresh to get product IDs
    p_laptop = db.query(Product).filter(Product.name == "Quantum Laptop").first()
    p_mouse = db.query(Product).filter(Product.name == "Wireless Mouse").first()
    p_monitor = db.query(Product).filter(Product.name == "AI Developer Monitor").first()
    
    if alice and bob and p_laptop and p_mouse and p_monitor:
        now = datetime.now(timezone.utc)
        orders = [
            # Alice bought a laptop 5 days ago (delivered, can be returned)
            Order(user_id=alice.id, product_id=p_laptop.id, quantity=1, total_price=1999.99, status="delivered", order_date=now - timedelta(days=7), delivery_date=now - timedelta(days=5)),
            # Alice bought mice 20 days ago (delivered, cannot be returned)
            Order(user_id=alice.id, product_id=p_mouse.id, quantity=2, total_price=119.98, status="delivered", order_date=now - timedelta(days=22), delivery_date=now - timedelta(days=20)),
            # Alice has a monitor in her cart
            Order(user_id=alice.id, product_id=p_monitor.id, quantity=1, total_price=699.00, status="in_cart"),
            # Bob bought a laptop
            Order(user_id=bob.id, product_id=p_laptop.id, quantity=2, total_price=3999.98, status="processing", order_date=now - timedelta(days=1)),
        ]
        for o in orders:
            db.add(o)
        db.commit()

    logger.info("Seeded e-commerce data.")


def seed_all() -> None:
    """Initialize DB and seed everything."""
    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
        seed_documents(db)
        seed_ecommerce(db)
    finally:
        db.close()
    logger.info("Database seeding complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed_all()
