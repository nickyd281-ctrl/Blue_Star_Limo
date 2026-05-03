from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from dotenv import load_dotenv
import psycopg2
import uuid
import os
import io
import traceback
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import smtplib
from email.mime.text import MIMEText
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

app = Flask(__name__)
CORS(app)

PRICING = {"JFK": 250, "LGA": 290, "HVN": 100}

AIRPORT_LABELS = {
    "JFK": "JFK — John F. Kennedy International Airport",
    "LGA": "LGA — LaGuardia Airport",
    "HVN": "HVN — Tweed New Haven Airport",
}


# ─── DB ───────────────────────────────────────────────────────────────────────

def get_db():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        dbname="bluestar_limo",
        user="postgres",
        password=os.environ.get("DB_PASSWORD"),
        host="localhost",
        port="5432"
    )


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id SERIAL PRIMARY KEY,
            date TEXT,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            destination TEXT,
            price INTEGER DEFAULT 0,
            email TEXT,
            invoice_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT,
            reviewtext TEXT NOT NULL,
            stars INTEGER DEFAULT 5,
            approved INTEGER DEFAULT 0,
            adminreply TEXT,
            createdat TEXT NOT NULL
        )
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM reviews")
    if cursor.fetchone()[0] == 0:
        seeds = [
            ("Michael T.", "Corporate Client — Stamford, CT", "Absolutely flawless service from start to finish. The Escalade was spotless, Ashish was punctual and incredibly professional. Blue Star Limo is my go-to for every airport run.", 5, 1, None, "2025-01-01 00:00:00"),
            ("Jennifer & David R.", "Wedding Clients — Greenwich, CT", "We used Blue Star for our wedding day and it was perfect. Sonal was so attentive during booking and made everything completely stress-free. Could not recommend them more!", 5, 1, None, "2025-01-02 00:00:00"),
            ("Robert K.", "Frequent Traveler — New Haven, CT", "I've used many car services across Connecticut, but none come close to Blue Star. The XT6 was luxurious and the ride was smooth. I will not use any other service.", 5, 1, None, "2025-01-03 00:00:00"),
        ]
        cursor.executemany(
            "INSERT INTO reviews (name, location, reviewtext, stars, approved, adminreply, createdat) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            seeds
        )
    conn.commit()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pricing (
            destination TEXT PRIMARY KEY,
            price INTEGER NOT NULL
        )
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM pricing")
    if cursor.fetchone()[0] == 0:
        for dest, price in PRICING.items():
            cursor.execute("INSERT INTO pricing (destination, price) VALUES (%s, %s)", (dest, price))
    conn.commit()
    conn.close()


# ─── Helpers ──────────────────────────────────────────────────────────────────

def parse_price(raw):
    if raw is None:
        return 0
    try:
        return int(str(raw).replace("$", "").strip())
    except ValueError:
        return 0


def row_to_review(row):
    return {
        "id":       row[0],
        "name":     row[1],
        "location": row[2] or "",
        "text":     row[3],
        "stars":    row[4],
        "approved": bool(row[5]),
        "reply":    row[6] or "",
        "created_at": row[7],
    }


def row_to_trip(row):
    return {
        "id":          row[0],
        "date":        row[1],
        "first_name":  row[2],
        "last_name":   row[3],
        "phone":       row[4],
        "destination": row[5],
        "price":       parse_price(row[6]),
        "email":       row[7] if len(row) > 7 else "",
        "invoice_id":  row[8] if len(row) > 8 else None,
    }


def get_pricing():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT destination, price FROM pricing")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows} if rows else PRICING


# ─── Email ────────────────────────────────────────────────────────────────────

def send_admin_notification(first_name, last_name, phone, email, destination, date, price, invoice_url):
    try:
        base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5001")
        msg = MIMEText(f"""
New booking received on Blue Star Limo.

Customer Details:
Name:        {first_name} {last_name}
Phone:       {phone}
Email:       {email or "Not provided"}

Trip Details:
Destination: {destination}
Date:        {date}
Price:       ${price}

View invoice:
{base_url}{invoice_url}
""")
        msg["Subject"] = f"New Booking — {first_name} {last_name} ({destination}, {date})"
        msg["From"] = "limobluestar1@gmail.com"
        msg["To"] = "limobluestar1@gmail.com"

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("limobluestar1@gmail.com", os.environ.get("EMAIL_PASSWORD", ""))
            server.send_message(msg)

    except Exception as e:
        print("Admin notification failed:", e)


def send_confirmation_email(to_email, first_name, destination, date, invoice_url):
    try:
        msg = MIMEText(f"""
Hello {first_name},

Your ride has been successfully booked.

Trip Details:
Destination: {destination}
Date: {date}

You can view your invoice here:
{os.environ.get("BASE_URL", "http://127.0.0.1:5001")}{invoice_url}

Thank you for choosing Blue Star Limo.
""")
        msg["Subject"] = "Blue Star Limo - Booking Confirmation"
        msg["From"] = "limobluestar1@gmail.com"
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login("limobluestar1@gmail.com", os.environ.get("EMAIL_PASSWORD", ""))
            server.send_message(msg)

    except Exception as e:
        print("Email failed:", e)


# ─── HTML Pages ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/contact")
@app.route("/contact.html")
@app.route("/Contact.html")
def contact():
    return send_from_directory(BASE_DIR, "contact.html")

@app.route("/team")
@app.route("/team.html")
@app.route("/Team.html")
def team():
    return send_from_directory(BASE_DIR, "team.html")

@app.route("/services")
@app.route("/services.html")
@app.route("/Services.html")
def services():
    return send_from_directory(BASE_DIR, "services.html")

@app.route("/admin")
@app.route("/trips.html")
def admin():
    return send_from_directory(BASE_DIR, "trips.html")

@app.route("/invoice/<invoice_id>")
def invoice_page(invoice_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE invoice_id = %s", (invoice_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return "Invoice not found.", 404

    trip = row_to_trip(row)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Booking Confirmed — Blue Star Limo</title>
  <link rel="stylesheet" href="/css/styles.css">
  <style>
    .invoice-wrap {{ display:flex; align-items:center; justify-content:center; min-height:calc(100vh - 80px); }}
    .invoice-box {{ max-width:540px; width:90%; background:#1a1a1a; border:1px solid #2a2a2a; padding:48px 40px; text-align:center; }}
    .invoice-box h1 {{ color:#c9a84c; font-size:24px; letter-spacing:1px; margin:0 0 24px; }}
    .invoice-table {{ width:100%; border-collapse:collapse; margin:24px 0; text-align:left; }}
    .invoice-table td {{ padding:10px 0; color:#aaa; font-size:14px; border-bottom:1px solid #2a2a2a; }}
    .invoice-table td:last-child {{ color:#fff; text-align:right; }}
    .invoice-total td {{ color:#c9a84c !important; font-weight:700; font-size:16px; }}
    .invoice-id {{ color:#555; font-size:11px; margin-top:20px; }}
    .btn-home {{ display:inline-block; margin-top:28px; background:#c9a84c; color:#000; padding:12px 28px;
                 font-weight:700; text-decoration:none; letter-spacing:2px; font-size:11px; text-transform:uppercase; }}
  </style>
</head>
<body>
  <nav class="nav">
    <span class="nav-brand">Blue Star Limo</span>
    <div class="nav-links">
      <a class="navitem" href="/">Home</a>
      <a class="navitem" href="/team">Our Team</a>
      <a class="navitem" href="/services">Services</a>
      <a class="navitem" href="/contact">Book a Ride</a>
    </div>
  </nav>
  <div class="invoice-wrap">
    <div class="invoice-box">
      <div style="font-size:40px;margin-bottom:16px;">&#10003;</div>
      <h1>Booking Confirmed!</h1>
      <table class="invoice-table">
        <tr><td>Name</td><td>{trip['first_name']} {trip['last_name']}</td></tr>
        <tr><td>Date</td><td>{trip['date']}</td></tr>
        <tr><td>Destination</td><td>{trip['destination']}</td></tr>
        <tr><td>Phone</td><td>{trip['phone']}</td></tr>
        <tr class="invoice-total"><td>Estimated Fare</td><td>${trip['price']}</td></tr>
      </table>
      <p style="color:#aaa;font-size:13px;">We'll be in touch shortly to confirm your pickup details.</p>
      <p class="invoice-id">Booking ID: {trip['invoice_id']}</p>
      <a href="/contact" class="btn-home">Book Another Ride</a>
    </div>
  </div>
</body>
</html>"""


# ─── Static Assets ────────────────────────────────────────────────────────────

@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(BASE_DIR, "css"), filename)

@app.route("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory(os.path.join(BASE_DIR, "images"), filename)


# ─── API: Admin Login ────────────────────────────────────────────────────────

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    password = data.get("password", "")
    correct = os.environ.get("ADMIN_PASSWORD", "")
    if password == correct:
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401


# ─── API: Trips ───────────────────────────────────────────────────────────────

@app.route("/api/trips", methods=["GET"])
def get_trips():
    destination = request.args.get("destination")
    conn = get_db()
    cursor = conn.cursor()
    if destination:
        cursor.execute(
            "SELECT * FROM trips WHERE destination ILIKE %s ORDER BY id DESC",
            (destination,)
        )
    else:
        cursor.execute("SELECT * FROM trips ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_trip(r) for r in rows])


# ─── API: Create Booking ──────────────────────────────────────────────────────

@app.route("/api/book", methods=["POST"])
def create_booking():
    try:
        date        = request.form.get("date")
        first_name  = request.form.get("first_name")
        last_name   = request.form.get("last_name")
        phone       = request.form.get("phone")
        destination = request.form.get("destination")
        email       = request.form.get("email")
        invoice_id  = str(uuid.uuid4())

        price = get_pricing().get(destination.upper(), 0) if destination else 0

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trips (date, first_name, last_name, phone, destination, price, email, invoice_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (date, first_name, last_name, phone, destination, price, email, invoice_id))
        conn.commit()
        conn.close()

        invoice_url = f"/invoice/{invoice_id}"

        send_admin_notification(first_name, last_name, phone, email, destination, date, price, invoice_url)

        if email:
            send_confirmation_email(email, first_name, destination, date, invoice_url)

        return jsonify({
            "message":     "Booking confirmed.",
            "invoice_url": invoice_url,
        })

    except Exception:
        print(f'Error:\n{traceback.format_exc()}')
        return jsonify({"error": "Booking failed."}), 500

# ─── API: Delete Trip ─────────────────────────────────────────────────────────

@app.route("/api/delete/<int:trip_id>", methods=["DELETE"])
def delete_trip(trip_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trips WHERE id = %s", (trip_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted"})


# ─── API: Invoice PDF ─────────────────────────────────────────────────────────

@app.route("/api/invoice/<int:trip_id>", methods=["GET"])
def generate_invoice(trip_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE id = %s", (trip_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Trip not found"}), 404

    trip = row_to_trip(row)

    buffer = io.BytesIO()
    W = 7.2 * inch
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    GOLD    = colors.HexColor("#c9a84c")
    DARK    = colors.HexColor("#0d1117")
    DARK2   = colors.HexColor("#161b22")
    CREAM   = colors.HexColor("#f8f5ef")
    MUTED   = colors.HexColor("#888888")
    LIGHT   = colors.HexColor("#aaaaaa")
    BORDER  = colors.HexColor("#dddddd")
    NOTE_BG = colors.HexColor("#fdf8f0")
    WHITE   = colors.white

    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    # Header styles (on dark bg)
    s_company  = ps("Co",  fontSize=24, textColor=GOLD,  fontName="Helvetica-Bold")
    s_tagline  = ps("Tag", fontSize=9,  textColor=LIGHT, fontName="Helvetica", spaceAfter=2)
    s_contact  = ps("Con", fontSize=9,  textColor=LIGHT, fontName="Helvetica")
    s_inv_word = ps("IW",  fontSize=30, textColor=WHITE, fontName="Helvetica-Bold",  alignment=TA_RIGHT)
    s_inv_num  = ps("IN",  fontSize=12, textColor=GOLD,  fontName="Helvetica-Bold",  alignment=TA_RIGHT, spaceBefore=3)
    s_inv_date = ps("ID",  fontSize=9,  textColor=LIGHT, alignment=TA_RIGHT, spaceAfter=0)

    # Info section styles (on white)
    s_lbl      = ps("Lbl",  fontSize=7,  textColor=GOLD,  fontName="Helvetica-Bold", letterSpacing=2, spaceAfter=5)
    s_name     = ps("Nm",   fontSize=15, textColor=DARK,  fontName="Helvetica-Bold", spaceAfter=4)
    s_info     = ps("Inf",  fontSize=10, textColor=colors.HexColor("#444444"), spaceAfter=3)
    s_tlbl     = ps("TLbl", fontSize=8,  textColor=MUTED, fontName="Helvetica-Bold", letterSpacing=1, spaceAfter=2)
    s_tval     = ps("TVl",  fontSize=11, textColor=DARK,  fontName="Helvetica-Bold", spaceAfter=10)

    # Table header/cell styles
    s_th   = ps("TH",  fontSize=9,  fontName="Helvetica-Bold", textColor=WHITE)
    s_th_c = ps("THC", fontSize=9,  fontName="Helvetica-Bold", textColor=WHITE,  alignment=TA_CENTER)
    s_th_r = ps("THR", fontSize=9,  fontName="Helvetica-Bold", textColor=WHITE,  alignment=TA_RIGHT)
    s_td   = ps("TD",  fontSize=11, textColor=DARK)
    s_td_s = ps("TDS", fontSize=9,  textColor=MUTED, spaceAfter=0)
    s_td_c = ps("TDC", fontSize=11, textColor=DARK,  alignment=TA_CENTER)
    s_td_r = ps("TDR", fontSize=11, textColor=DARK,  alignment=TA_RIGHT)

    s_total_lbl = ps("TLbl2", fontSize=9,  textColor=MUTED, fontName="Helvetica-Bold", alignment=TA_RIGHT, letterSpacing=2)
    s_total_val = ps("TVl2",  fontSize=30, textColor=GOLD,  fontName="Helvetica-Bold", alignment=TA_RIGHT)

    s_note_lbl  = ps("NLbl", fontSize=7,  textColor=GOLD,  fontName="Helvetica-Bold", letterSpacing=2, spaceAfter=5)
    s_note_body = ps("NB",   fontSize=9,  textColor=colors.HexColor("#666666"), leading=14)

    s_foot      = ps("Ft",  fontSize=8, textColor=MUTED, alignment=TA_CENTER)
    s_foot_i    = ps("FtI", fontSize=8, textColor=MUTED, alignment=TA_CENTER,
                     spaceBefore=4, fontName="Helvetica-Oblique")

    # Computed values
    invoice_num   = f"BSL-{trip['id']:04d}"
    issued_date   = datetime.now().strftime("%B %d, %Y")
    dest_label    = AIRPORT_LABELS.get(trip["destination"], trip["destination"])
    price_str     = f"${trip['price']:,}"
    try:
        trip_date = datetime.strptime(trip["date"], "%Y-%m-%d").strftime("%B %d, %Y")
    except Exception:
        trip_date = trip["date"] or "—"

    story = []

    # ── 1. HEADER ─────────────────────────────────────────────────────────────
    hdr = Table([
        [Paragraph("Blue Star Limo", s_company),
         Paragraph("INVOICE", s_inv_word)],
        [Paragraph("Connecticut's Premier Luxury Transportation", s_tagline),
         Paragraph(invoice_num, s_inv_num)],
        [Paragraph("limobluestar1@gmail.com  ·  Available 24/7", s_contact),
         Paragraph(f"Issued: {issued_date}", s_inv_date)],
    ], colWidths=[4.4 * inch, 2.8 * inch])

    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK2),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 22),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 22),
        ("TOPPADDING",    (0, 0), (-1, 0),  26),
        ("TOPPADDING",    (0, 1), (-1, 1),  5),
        ("TOPPADDING",    (0, 2), (-1, 2),  4),
        ("BOTTOMPADDING", (0, 0), (-1, 1),  2),
        ("BOTTOMPADDING", (0, 2), (-1, 2),  26),
    ]))

    story.append(hdr)
    story.append(HRFlowable(width="100%", thickness=4, color=GOLD,
                             spaceBefore=0, spaceAfter=28))

    # ── 2. BILL TO + TRIP DETAILS (two columns) ───────────────────────────────
    bill_cells = [
        Paragraph("BILL TO", s_lbl),
        Paragraph(f"{trip['first_name']} {trip['last_name']}", s_name),
    ]
    if trip["phone"]:
        bill_cells.append(Paragraph(trip["phone"], s_info))
    if trip["email"]:
        bill_cells.append(Paragraph(trip["email"], s_info))

    trip_cells = [
        Paragraph("TRIP DETAILS", s_lbl),
        Paragraph("DESTINATION", s_tlbl),
        Paragraph(dest_label, s_tval),
        Paragraph("PICKUP DATE", s_tlbl),
        Paragraph(trip_date, s_tval),
        Paragraph("INVOICE NO.", s_tlbl),
        Paragraph(invoice_num, s_tval),
    ]

    info_tbl = Table([[bill_cells, trip_cells]],
                     colWidths=[3.9 * inch, 3.3 * inch])
    info_tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 22))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=16))

    # ── 3. SERVICE TABLE ──────────────────────────────────────────────────────
    svc_tbl = Table([
        [Paragraph("DESCRIPTION", s_th),
         Paragraph("PICKUP DATE", s_th_c),
         Paragraph("AMOUNT", s_th_r)],
        [[Paragraph(f"Airport Transfer — {dest_label}", s_td),
          Paragraph(f"Booking ref: {trip['invoice_id']}", s_td_s)],
         Paragraph(trip_date, s_td_c),
         Paragraph(price_str, s_td_r)],
    ], colWidths=[3.9 * inch, 1.5 * inch, 1.8 * inch])

    svc_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0), DARK),
        ("BACKGROUND",    (0, 1), (-1, -1), CREAM),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("LINEBELOW",     (0, 0), (-1,  0), 3, GOLD),
        ("LINEBELOW",     (0,-1), (-1, -1), 1, BORDER),
    ]))

    story.append(svc_tbl)
    story.append(Spacer(1, 4))

    # ── 4. TOTAL ──────────────────────────────────────────────────────────────
    tot_tbl = Table([
        ["",
         Paragraph("ESTIMATED TOTAL", s_total_lbl),
         Paragraph(price_str, s_total_val)],
    ], colWidths=[3.9 * inch, 1.5 * inch, 1.8 * inch])

    tot_tbl.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEABOVE",     (1, 0), (-1,  0), 2, GOLD),
        ("VALIGN",        (0, 0), (-1, -1), "BOTTOM"),
    ]))

    story.append(tot_tbl)
    story.append(Spacer(1, 28))

    # ── 5. NOTES ──────────────────────────────────────────────────────────────
    note_tbl = Table([[
        [Paragraph("PLEASE NOTE", s_note_lbl),
         Paragraph(
             "This is an estimated fare. Final charges may vary based on actual distance, "
             "traffic conditions, tolls, and any additional stops or waiting time. "
             "Payment is due upon completion of service.",
             s_note_body,
         )]
    ]], colWidths=[W])

    note_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NOTE_BG),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LINEBELOW",     (0, 0), (-1, -1), 2, GOLD),
    ]))

    story.append(note_tbl)
    story.append(Spacer(1, 36))

    # ── 6. FOOTER ─────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=10))
    story.append(Paragraph(
        "Blue Star Limo LLC  ·  Connecticut's Premier Luxury Transportation  ·  "
        "limobluestar1@gmail.com  ·  Available 24/7",
        s_foot
    ))
    story.append(Paragraph(
        "Thank you for choosing Blue Star Limo — we look forward to serving you.",
        s_foot_i
    ))

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"BlueStar-Invoice-{invoice_num}.pdf",
        mimetype="application/pdf"
    )


# ─── API: Reviews (Public) ────────────────────────────────────────────────────

@app.route("/api/reviews", methods=["GET"])
def get_reviews():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews WHERE approved = 1 ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_review(r) for r in rows])


@app.route("/api/reviews", methods=["POST"])
def submit_review():
    data     = request.get_json() or {}
    name     = (data.get("name", "") or "").strip()
    location = (data.get("location", "") or "").strip()
    text     = (data.get("text", "") or "").strip()
    stars    = int(data.get("stars", 5))

    if not name or not text:
        return jsonify({"error": "Name and review text are required."}), 400
    if not (1 <= stars <= 5):
        stars = 5

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reviews (name, location, reviewtext, stars, approved, adminreply, createdat) VALUES (%s, %s, %s, %s, 0, NULL, %s)",
        (name, location, text, stars, created_at),
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Thank you! Your review has been submitted and will appear after approval."})


# ─── API: Reviews (Admin) ─────────────────────────────────────────────────────

@app.route("/api/reviews/all", methods=["GET"])
def get_all_reviews():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reviews ORDER BY approved ASC, id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_review(r) for r in rows])


@app.route("/api/reviews/<int:review_id>/approve", methods=["POST"])
def approve_review(review_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE reviews SET approved = 1 WHERE id = %s", (review_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Review approved.", "id": review_id})


@app.route("/api/reviews/<int:review_id>/reply", methods=["POST"])
def reply_review(review_id):
    data   = request.get_json() or {}
    reply  = (data.get("reply", "") or "").strip()
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE reviews SET adminreply = %s WHERE id = %s", (reply or None, review_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Reply saved.", "id": review_id})


@app.route("/api/reviews/<int:review_id>", methods=["DELETE"])
def delete_review(review_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Review deleted.", "id": review_id})


# ─── API: Pricing ────────────────────────────────────────────────────────────

@app.route("/api/pricing", methods=["GET"])
def list_pricing():
    return jsonify(get_pricing())


@app.route("/api/pricing/<destination>", methods=["POST"])
def update_destination_price(destination):
    data = request.get_json() or {}
    try:
        price = int(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid price."}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pricing (destination, price) VALUES (%s, %s) "
        "ON CONFLICT (destination) DO UPDATE SET price = EXCLUDED.price",
        (destination.upper(), price)
    )
    conn.commit()
    conn.close()
    return jsonify({"destination": destination.upper(), "price": price})


@app.route("/api/trips/<int:trip_id>/price", methods=["PATCH"])
def update_trip_price(trip_id):
    data = request.get_json() or {}
    try:
        price = int(data.get("price", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid price."}), 400
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE trips SET price = %s WHERE id = %s", (price, trip_id))
    conn.commit()
    conn.close()
    return jsonify({"id": trip_id, "price": price})


# ─── Startup ──────────────────────────────────────────────────────────────────

try:
    init_db()
except Exception as e:
    print(f"DB init warning: {e}")

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)