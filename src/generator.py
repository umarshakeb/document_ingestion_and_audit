import os
import random
from faker import Faker
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

fake = Faker()

def generate_alphanumeric_code(category):
    """Generates messy, realistic manufacturing/logistics part numbers."""
    prefixes = {
        "tire": ["TYR", "TR", "WHL", "TIRE"],
        "engine": ["ENG", "EN", "MOT", "PWR"],
        "fastener": ["FST", "BLT", "NUT", "SCR"]
    }
    pref = random.choice(prefixes.get(category, ["PART"]))
    num1 = random.randint(100, 999)
    num2 = random.randint(10, 99)
    suffix = random.choice(["A", "X", "V1", "MAX", "HD", "DOT"])
    
    # Intentionally vary patterns to simulate messy documents
    pattern = random.choice([
        f"{pref}-{num1}-{num2}R{suffix}",
        f"{pref}.{num1}.{num2}.{suffix}",
        f"{pref}{num1}X{num2}_{suffix}"
    ])
    return pattern

def create_invoice_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    # Modify existing style or add unique custom names to avoid conflicts
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=24, leading=28, textColor=colors.HexColor("#1A365D"))
    meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontSize=10, leading=14)
    
    # Randomize headers to simulate disparate vendor layouts
    vendor_name = fake.company()
    invoice_id = f"INV-{random.randint(2025, 2026)}-{random.choice(['XF','KL','BD'])}{random.randint(1000, 9999)}"
    date = fake.date_between(start_date='-1y', end_date='today').strftime('%Y-%m-%d')
    
    story.append(Paragraph(f"INVOICE: {vendor_name}", title_style))
    story.append(Spacer(1, 15))
    
    # Meta layout matrix
    meta_text = f"<b>Invoice ID:</b> {invoice_id}<br/><b>Date:</b> {date}<br/><b>PO Reference:</b> PO-{random.randint(50000, 99999)}"
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 20))
    
    # Table Header data
    table_data = [["Item Code", "Description", "Qty", "Unit Price", "Total"]]
    
    # Generate line items
    categories = ["tire", "engine", "fastener"]
    num_items = random.randint(3, 8)
    subtotal = 0.0
    
    for _ in range(num_items):
        cat = random.choice(categories)
        code = generate_alphanumeric_code(cat)
        desc = f"{fake.catch_phrase()} ({cat.upper()} Assembly)"
        qty = random.randint(1, 50)
        price = round(random.uniform(15.0, 1200.0), 2)
        total = round(qty * price, 2)
        subtotal += total
        
        # Randomly omit description text to challenge our parsing agent logic
        if random.random() < 0.15:
            desc = ""
            
        table_data.append([code, desc, str(qty), f"${price:,}", f"${total:,}"])
        
    table_data.append(["", "", "", "Subtotal:", f"${round(subtotal, 2):,}"])
    
    # Style the tabular grid layout
    invoice_table = Table(table_data, colWidths=[140, 200, 40, 70, 80])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('LINEABOVE', (3, -1), (-1, -1), 1, colors.HexColor("#1A365D")),
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(invoice_table)
    doc.build(story)

if __name__ == "__main__":
    output_dir = os.path.join("data", "raw_synthetic")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Generating 10 messy enterprise invoices in {output_dir}...")
    for i in range(1, 11):
        filename = os.path.join(output_dir, f"invoice_mock_{i:02d}.pdf")
        create_invoice_pdf(filename)
    print("Generation complete! Check your data/raw_synthetic folder.")