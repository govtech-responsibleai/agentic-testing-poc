from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import pandas as pd
import random
import os
import sqlite3
import pathlib
from datetime import datetime, timedelta

BASE = pathlib.Path(__file__).parent / "docs"
PDF_DIR, CSV_DIR = BASE/"pdf", BASE/"csv"
DB_PATH = pathlib.Path(__file__).parent / "business.sqlite"

def ensure_dirs():
    for p in (PDF_DIR, CSV_DIR):
        p.mkdir(parents=True, exist_ok=True)

def build_csvs(fake: Faker):
    # Products
    products = []
    categories = ["Office Supplies", "Electronics", "Furniture", "Stationery"]
    for i in range(50):
        products.append({
            "sku": f"P{1000+i}",
            "name": fake.word().title() + " " + random.choice(["Pro", "Plus", "Basic", "Deluxe"]),
            "category": random.choice(categories),
            "price": round(random.uniform(5, 200), 2),
            "stock": random.randint(0, 100)
        })
    
    # Customers
    customers = []
    for i in range(25):
        customers.append({
            "customer_id": i+1,
            "name": fake.company(),
            "contact_name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.address().replace('\n', ', ')
        })
    
    # Orders
    orders = []
    order_details = []
    order_id = 1
    start_date = datetime.now() - timedelta(days=90)
    
    for _ in range(150):
        customer = random.choice(customers)
        order_date = start_date + timedelta(days=random.randint(0, 90))
        
        order = {
            "order_id": order_id,
            "customer_id": customer["customer_id"],
            "order_date": order_date.strftime("%Y-%m-%d"),
            "status": random.choice(["Pending", "Shipped", "Delivered", "Cancelled"])
        }
        orders.append(order)
        
        # Order details (1-5 unique items per order)
        num_items = random.randint(1, 5)
        selected_products = random.sample(products, min(num_items, len(products)))
        for product in selected_products:
            qty = random.randint(1, 10)
            order_details.append({
                "order_id": order_id,
                "sku": product["sku"],
                "quantity": qty,
                "unit_price": product["price"],
                "total": round(qty * product["price"], 2)
            })
        
        order_id += 1
    
    # Save CSVs
    pd.DataFrame(products).to_csv(CSV_DIR/"products.csv", index=False)
    pd.DataFrame(customers).to_csv(CSV_DIR/"customers.csv", index=False)
    pd.DataFrame(orders).to_csv(CSV_DIR/"orders.csv", index=False)
    pd.DataFrame(order_details).to_csv(CSV_DIR/"order_details.csv", index=False)

def build_pdfs(fake: Faker):
    # Generate sample invoices
    for i in range(15):
        file_path = PDF_DIR / f"invoice_{str(i+1).zfill(3)}.pdf"
        c = canvas.Canvas(str(file_path), pagesize=A4)
        
        # Header
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 800, "ACME OFFICE SUPPLIES")
        c.setFont("Helvetica", 10)
        c.drawString(100, 780, "123 Business Ave, Commerce City, NY 10001")
        c.drawString(100, 765, "Phone: (555) 123-4567 | Email: sales@acme-office.com")
        
        # Invoice details
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, 720, f"INVOICE #{str(i+1).zfill(6)}")
        
        c.setFont("Helvetica", 10)
        invoice_date = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d")
        c.drawString(100, 700, f"Date: {invoice_date}")
        c.drawString(100, 685, f"Due Date: {(datetime.strptime(invoice_date, '%Y-%m-%d') + timedelta(days=30)).strftime('%Y-%m-%d')}")
        
        # Customer info
        c.drawString(100, 650, "Bill To:")
        c.drawString(100, 635, fake.company())
        c.drawString(100, 620, fake.name())
        c.drawString(100, 605, fake.address().replace('\n', ', '))
        
        # Items
        y = 550
        c.drawString(100, y, "Item")
        c.drawString(300, y, "Qty")
        c.drawString(350, y, "Price")
        c.drawString(450, y, "Total")
        
        y -= 20
        total_amount = 0
        for j in range(random.randint(1, 5)):
            item_name = fake.word().title() + " " + random.choice(["Supplies", "Equipment", "Materials"])
            qty = random.randint(1, 10)
            price = round(random.uniform(10, 100), 2)
            line_total = qty * price
            total_amount += line_total
            
            c.drawString(100, y, item_name[:25])
            c.drawString(300, y, str(qty))
            c.drawString(350, y, f"${price}")
            c.drawString(450, y, f"${line_total:.2f}")
            y -= 15
        
        # Total
        c.setFont("Helvetica-Bold", 12)
        c.drawString(400, y-20, f"TOTAL: ${total_amount:.2f}")
        
        c.save()
    
    # Generate expense receipts
    for i in range(10):
        file_path = PDF_DIR / f"expense_receipt_{str(i+1).zfill(3)}.pdf"
        c = canvas.Canvas(str(file_path), pagesize=A4)
        
        c.setFont("Helvetica-Bold", 14)
        vendor = fake.company()
        c.drawString(100, 800, vendor)
        
        c.setFont("Helvetica", 10)
        receipt_date = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        c.drawString(100, 780, f"Receipt Date: {receipt_date}")
        c.drawString(100, 765, f"Receipt #: R{random.randint(10000, 99999)}")
        
        expense_types = ["Office Supplies", "Travel", "Meals", "Equipment", "Software"]
        expense_type = random.choice(expense_types)
        amount = round(random.uniform(25, 500), 2)
        
        c.drawString(100, 720, f"Expense Type: {expense_type}")
        c.drawString(100, 705, f"Description: {fake.sentence()}")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, 680, f"Amount: ${amount}")
        
        c.save()

def build_sqlite():
    if DB_PATH.exists():
        DB_PATH.unlink()
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Create tables
    cur.executescript("""
    CREATE TABLE products (
        sku TEXT PRIMARY KEY,
        name TEXT,
        category TEXT,
        price REAL,
        stock INTEGER
    );
    
    CREATE TABLE customers (
        customer_id INTEGER PRIMARY KEY,
        name TEXT,
        contact_name TEXT,
        email TEXT,
        phone TEXT,
        address TEXT
    );
    
    CREATE TABLE orders (
        order_id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        order_date TEXT,
        status TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
    );
    
    CREATE TABLE order_details (
        order_id INTEGER,
        sku TEXT,
        quantity INTEGER,
        unit_price REAL,
        total REAL,
        PRIMARY KEY (order_id, sku),
        FOREIGN KEY (order_id) REFERENCES orders (order_id),
        FOREIGN KEY (sku) REFERENCES products (sku)
    );
    """)
    
    # Load data from CSVs
    products_df = pd.read_csv(CSV_DIR/"products.csv")
    customers_df = pd.read_csv(CSV_DIR/"customers.csv")
    orders_df = pd.read_csv(CSV_DIR/"orders.csv")
    order_details_df = pd.read_csv(CSV_DIR/"order_details.csv")
    
    # Insert data
    products_df.to_sql('products', conn, if_exists='append', index=False)
    customers_df.to_sql('customers', conn, if_exists='append', index=False)
    orders_df.to_sql('orders', conn, if_exists='append', index=False)
    order_details_df.to_sql('order_details', conn, if_exists='append', index=False)
    
    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}")

def generate_meeting_minutes(fake: Faker):
    """Generate 50 realistic meeting minutes documents"""
    MINUTES_DIR = BASE / "meeting_minutes"
    MINUTES_DIR.mkdir(exist_ok=True)
    
    # Meeting types and their typical topics
    meeting_types = {
        "Weekly Sales Review": [
            "sales performance", "pipeline updates", "customer feedback", "market trends",
            "quarterly targets", "lead generation", "competitor analysis", "pricing strategy"
        ],
        "Product Development": [
            "feature roadmap", "user testing results", "technical challenges", "release timeline",
            "bug fixes", "performance improvements", "customer requirements", "design updates"
        ],
        "Board Meeting": [
            "financial performance", "strategic initiatives", "market expansion", "risk management",
            "regulatory compliance", "partnership opportunities", "investment decisions", "governance"
        ],
        "Operations Review": [
            "supply chain", "inventory management", "process improvements", "quality control",
            "vendor relationships", "cost optimization", "capacity planning", "efficiency metrics"
        ],
        "HR Committee": [
            "employee satisfaction", "recruitment", "training programs", "performance reviews",
            "compensation", "company culture", "diversity initiatives", "retention strategies"
        ],
        "Marketing Strategy": [
            "campaign performance", "brand awareness", "digital marketing", "content strategy",
            "social media", "customer acquisition", "market research", "advertising budget"
        ],
        "Finance Committee": [
            "budget review", "cash flow", "financial projections", "cost analysis",
            "investment portfolio", "audit findings", "tax planning", "expense management"
        ]
    }
    
    departments = ["Sales", "Marketing", "Finance", "Operations", "HR", "Product", "IT"]
    action_verbs = ["review", "implement", "analyze", "optimize", "develop", "improve", "monitor", "evaluate"]
    business_terms = ["ROI", "KPIs", "market share", "customer retention", "operational efficiency", 
                     "revenue growth", "cost reduction", "process improvement", "digital transformation"]
    
    for i in range(50):
        # Choose meeting type and related topics
        meeting_type = random.choice(list(meeting_types.keys()))
        topics = meeting_types[meeting_type]
        
        # Generate meeting date (last 6 months)
        meeting_date = fake.date_between(start_date='-6m', end_date='today')
        
        # Generate attendees (3-8 people)
        attendees = [fake.name() for _ in range(random.randint(3, 8))]
        chair = random.choice(attendees)
        
        # Start building the document
        content = []
        content.append(f"# {meeting_type}")
        content.append(f"**Date:** {meeting_date.strftime('%B %d, %Y')}")
        content.append(f"**Time:** {random.randint(9, 16)}:00 - {random.randint(10, 17)}:00")
        content.append(f"**Chair:** {chair}")
        content.append(f"**Attendees:** {', '.join(attendees)}")
        content.append("")
        
        # Agenda items (3-6 items)
        content.append("## Agenda")
        agenda_items = random.sample(topics, random.randint(3, 6))
        for j, item in enumerate(agenda_items, 1):
            content.append(f"{j}. {item.title()}")
        content.append("")
        
        # Discussion points
        content.append("## Discussion Summary")
        
        for item in agenda_items:
            content.append(f"### {item.title()}")
            
            # Generate 2-4 discussion points per agenda item
            discussion_points = []
            for _ in range(random.randint(2, 4)):
                department = random.choice(departments)
                action = random.choice(action_verbs)
                term = random.choice(business_terms)
                
                point_templates = [
                    f"{department} team reported {random.randint(5, 25)}% improvement in {term} compared to last quarter.",
                    f"Discussion on how to {action} {term} through better coordination with {random.choice(departments)}.",
                    f"Concerns raised about {item} impact on overall {term} and customer satisfaction.",
                    f"Proposal to {action} current {item} processes by Q{random.randint(2, 4)} {random.randint(2024, 2025)}.",
                    f"{random.choice(attendees)} presented analysis showing {random.randint(10, 30)}% variance in {term}.",
                    f"Need to {action} {item} strategy to align with company's focus on {term}.",
                    f"Budget allocation of ${random.randint(10, 500)}K approved for {item} improvements.",
                ]
                
                discussion_points.append(random.choice(point_templates))
            
            for point in discussion_points:
                content.append(f"- {point}")
            content.append("")
        
        # Action items (2-5 items)
        content.append("## Action Items")
        for j in range(random.randint(2, 5)):
            assignee = random.choice(attendees)
            due_date = meeting_date + timedelta(days=random.randint(7, 30))
            action = random.choice(action_verbs)
            topic = random.choice(agenda_items)
            
            action_templates = [
                f"**{assignee}** to {action} {topic} metrics and report back by {due_date.strftime('%m/%d/%Y')}",
                f"**{assignee}** to coordinate with {random.choice(departments)} team on {topic} by {due_date.strftime('%m/%d/%Y')}",
                f"**{assignee}** to prepare {topic} proposal for next meeting ({due_date.strftime('%m/%d/%Y')})",
                f"**{assignee}** to {action} current {topic} process and present findings by {due_date.strftime('%m/%d/%Y')}",
            ]
            
            content.append(f"{j+1}. {random.choice(action_templates)}")
        
        content.append("")
        content.append("## Next Meeting")
        next_meeting_date = meeting_date + timedelta(weeks=random.randint(1, 4))
        content.append(f"**Date:** {next_meeting_date.strftime('%B %d, %Y')}")
        content.append(f"**Focus:** Follow-up on action items and {random.choice(topics)} review")
        
        # Save the meeting minutes
        filename = f"meeting_{i+1:02d}_{meeting_type.lower().replace(' ', '_')}_{meeting_date.strftime('%Y%m%d')}.md"
        filepath = MINUTES_DIR / filename
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(content))
    
    print(f"Generated 50 meeting minutes")

def create_vector_db():
    """Create vector database for meeting minutes"""
    try:
        import chromadb
        import uuid
        
        MINUTES_DIR = BASE / "meeting_minutes" 
        CHROMA_DIR = pathlib.Path(__file__).parent / "chroma_db"
        
        # Create Chroma client with persistence
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        
        # Create or get collection
        collection = client.get_or_create_collection(
            name="business_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        if not MINUTES_DIR.exists():
            print("No meeting minutes found to index")
            return
        
        documents = []
        metadatas = []
        ids = []
        
        for file_path in MINUTES_DIR.glob("*.md"):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Extract metadata from filename
            filename = file_path.name
            parts = filename.split('_')
            meeting_num = parts[1]
            meeting_type = '_'.join(parts[2:-1])
            date_str = parts[-1].replace('.md', '')
            
            # Parse title from content
            lines = content.split('\n')
            meeting_title = lines[0].replace('# ', '') if lines else "Unknown Meeting"
            
            metadata = {
                "filename": filename,
                "meeting_number": meeting_num,
                "meeting_type": meeting_type.replace('_', ' ').title(),
                "date": date_str,
                "document_type": "meeting_minutes",
                "title": meeting_title
            }
            
            documents.append(content)
            metadatas.append(metadata)
            ids.append(str(uuid.uuid4()))
        
        # Add to collection
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Vector DB created with {len(documents)} documents")
        else:
            print("No documents to add to vector DB")
            
    except ImportError:
        print("Chromadb not available, skipping vector DB creation")
    except Exception as e:
        print(f"Vector DB creation failed: {e}")

def generate_all():
    fake = Faker()
    Faker.seed(42)  # For reproducible data
    random.seed(42)
    
    print("Creating directories...")
    ensure_dirs()
    
    print("Generating CSV files...")
    build_csvs(fake)
    
    print("Generating PDF files...")
    build_pdfs(fake)
    
    print("Generating meeting minutes...")
    generate_meeting_minutes(fake)
    
    print("Creating SQLite database...")
    build_sqlite()
    
    print("Creating vector database...")
    create_vector_db()
    
    print("Sample data generation complete!")

if __name__ == "__main__":
    generate_all()
