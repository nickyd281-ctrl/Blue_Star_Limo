from flask import Flask, jsonify, request, send_from_directory, make_response, send_file
from flask_cors import CORS
import sqlite3
import os
import io
import traceback
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "BlueStarLimo.db")

PRICING = {"JFK": 250, "LGA": 290, "HVN": 100}

AIRPORT_LABELS = {
    "JFK": "JFK — John F. Kennedy International Airport",
    "LGA": "LGA — LaGuardia Airport",
    "HVN": "HVN — Tweed New Haven Airport",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_db():
    return sqlite3.connect(DB_PATH)


def parse_price(raw):
    """Return price as int, handling legacy '$250' strings."""
    if raw is None:
        return 0
    try:
        return int(str(raw).replace("$", "").strip())
    except ValueError:
        return 0


def row_to_trip(row):
    return {
        "id":         row[0],
        "date":       row[1],
        "first_name": row[2],
        "last_name":  row[3],
        "phone":      row[4],
        "destination": row[5],
        "price":      parse_price(row[6]),
        "email":      row[7] if len(row) > 7 else "",
    }


# ─── HTML Pages ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/contact")
@app.route("/contact.html")
@app.route("/Contact.html")
def contact():
    return send_from_directory(BASE_DIR, "Contact.html")

@app.route("/team")
@app.route("/team.html")
@app.route("/Team.html")
def team():
    return send_from_directory(BASE_DIR, "Team.html")

@app.route("/services")
@app.route("/services.html")
@app.route("/Services.html")
def services():
    return send_from_directory(BASE_DIR, "Services.html")

@app.route("/admin")
@app.route("/trips.html")
def admin():
    return send_from_directory(BASE_DIR, "trips.html")


# ─── Static Assets ────────────────────────────────────────────────────────────

@app.route("/css/<path:filename>")
def serve_css(filename):
    return send_from_directory(os.path.join(BASE_DIR, "css"), filename)

@app.route("/images/<path:filename>")
def serve_images(filename):
    return send_from_directory(os.path.join(BASE_DIR, "images"), filename)


# ─── API: Get All Trips ───────────────────────────────────────────────────────

@app.route("/api/trips", methods=["GET"])
def get_trips():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Trips ORDER BY Id DESC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_trip(r) for r in rows])


# ─── API: Filter by Destination ──────────────────────────────────────────────

@app.route("/api/trips/<destination>", methods=["GET"])
def get_trips_by_destination(destination):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM Trips WHERE Destination = ? ORDER BY Id DESC",
        (destination.upper(),)
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify([row_to_trip(r) for r in rows])


# ─── API: Create Booking ──────────────────────────────────────────────────────

@app.route("/api/book", methods=["POST"])
def create_booking():
    try:
        date        = request.form.get("date", "").strip()
        first_name  = request.form.get("first_name", "").strip()
        last_name   = request.form.get("last_name", "").strip()
        phone       = request.form.get("phone", "").strip()
        destination = request.form.get("destination", "").strip().upper()
        email       = request.form.get("email", "").strip()

        price = PRICING.get(destination, 0)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO Trips (Dates, "First Name", "Last Name", "Phone Number", Destination, Price, Email) '
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (date, first_name, last_name, phone, destination, price, email),
        )
        conn.commit()
        conn.close()

        price_display = f"${price:,}" if price else "TBD (call for pricing)"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Booking Confirmed — Blue Star Limo</title>
  <link rel="stylesheet" href="/css/styles.css">
  <style>
    .confirm-wrap {{
      display: flex; align-items: center; justify-content: center;
      min-height: calc(100vh - 80px);
    }}
    .confirm-box {{
      max-width: 520px; width: 90%; text-align: center;
      padding: 48px 40px; background: #1a1a1a; border: 1px solid #2a2a2a;
    }}
    .confirm-icon {{ font-size: 48px; margin-bottom: 20px; }}
    .confirm-box h1 {{ color: #c9a84c; font-size: 26px; margin: 0 0 14px; letter-spacing: 1px; }}
    .confirm-box p  {{ color: #aaa; font-size: 14px; line-height: 1.8; margin-bottom: 28px; }}
    .confirm-box strong {{ color: #fff; }}
    .confirm-box a  {{
      display: inline-block; background: #c9a84c; color: #000;
      padding: 14px 32px; font-weight: 700; text-decoration: none;
      letter-spacing: 2px; font-size: 11px; text-transform: uppercase;
      transition: background 0.3s;
    }}
    .confirm-box a:hover {{ background: #e0c46c; }}
  </style>
</head>
<body>
  <nav class="nav">
    <span class="nav-brand">Blue Star Limo</span>
    <div class="nav-links">
      <a class="navitem" href="/">Home</a>
      <a class="navitem" href="/team">Our Team</a>
      <a class="navitem" href="/services">Services</a>
      <a class="navitem active" href="/contact">Book a Ride</a>
    </div>
  </nav>
  <div class="confirm-wrap">
    <div class="confirm-box">
      <div class="confirm-icon">✓</div>
      <h1>Booking Confirmed!</h1>
      <p>
        Thank you, <strong>{first_name} {last_name}</strong>!<br>
        Your reservation to <strong>{destination}</strong> on <strong>{date}</strong>
        has been received.<br><br>
        Estimated fare: <strong>{price_display}</strong><br><br>
        We will be in touch shortly to confirm your pickup details.
      </p>
      <a href="/contact">Book Another Ride</a>
    </div>
  </div>
</body>
</html>"""
    except Exception:
        print(f'Error:\n{traceback.format_exc()}')


# ─── API: Delete Trip ─────────────────────────────────────────────────────────

@app.route("/api/delete/<int:trip_id>", methods=["DELETE"])
def delete_trip(trip_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Trips WHERE Id = ?", (trip_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Trip deleted", "id": trip_id})


# ─── API: Invoice PDF ─────────────────────────────────────────────────────────

@app.route("/api/invoice/<int:trip_id>", methods=["GET"])
def generate_invoice(trip_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Trips WHERE Id = ?", (trip_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Trip not found"}), 404

    trip = row_to_trip(row)

    # 📄 Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    # 🎨 Colors
    GOLD   = colors.HexColor("#c9a84c")
    DARK   = colors.HexColor("#111111")
    CREAM  = colors.HexColor("#f5f0e8")
    MUTED  = colors.HexColor("#888888")
    BORDER = colors.HexColor("#cccccc")
    WHITE  = colors.white

    # 🎨 Styles
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    s_company = ps("Company", fontSize=30, textColor=GOLD, fontName="Helvetica-Bold", spaceAfter=4)
    s_tagline = ps("Tagline", fontSize=10, textColor=MUTED, fontName="Helvetica", spaceAfter=4)
    s_inv_label = ps("InvLabel", fontSize=36, textColor=DARK, fontName="Helvetica-Bold", alignment=TA_RIGHT)

    s_meta_r = ps("MetaR", fontSize=11, textColor=DARK, alignment=TA_RIGHT, spaceAfter=6)
    s_meta_r_sm = ps("MetaRSm", fontSize=10, textColor=DARK, alignment=TA_RIGHT)

    s_section = ps(
        "Section",
        fontSize=10,
        textColor=GOLD,
        fontName="Helvetica-Bold",
        spaceBefore=25,
        spaceAfter=10,
        letterSpacing=3
    )

    s_body = ps("Body", fontSize=11, textColor=DARK, spaceAfter=5)
    s_body_muted = ps("BodyMuted", fontSize=10, textColor=MUTED, spaceAfter=4)

    s_th = ps("TH", fontSize=10, fontName="Helvetica-Bold", textColor=WHITE)
    s_th_c = ps("THC", fontSize=10, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_CENTER)
    s_th_r = ps("THR", fontSize=10, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_RIGHT)

    s_td = ps("TD", fontSize=12, textColor=DARK)
    s_td_c = ps("TDC", fontSize=12, textColor=DARK, alignment=TA_CENTER)
    s_td_r = ps("TDR", fontSize=12, textColor=DARK, alignment=TA_RIGHT)

    s_total_lbl = ps("TotalLbl", fontSize=14, textColor=DARK, fontName="Helvetica-Bold", alignment=TA_RIGHT)
    s_total_val = ps("TotalVal", fontSize=28, textColor=GOLD, fontName="Helvetica-Bold", alignment=TA_RIGHT)

    s_footer = ps("Footer", fontSize=9, textColor=MUTED, alignment=TA_CENTER)
    s_footer_i = ps("FooterI", fontSize=9, textColor=MUTED, alignment=TA_CENTER, spaceBefore=6)

    # 🧾 Invoice Info
    invoice_num = f"BSL-{trip['id']:04d}"
    generated = datetime.now().strftime("%B %d, %Y")
    dest_label = AIRPORT_LABELS.get(trip["destination"], trip["destination"])

    story = []

    # =========================
    # HEADER
    # =========================
    hdr = Table([
        [Paragraph("Blue Star Limo", s_company),
         Paragraph("INVOICE", s_inv_label)],
        [Paragraph("Connecticut's Premier Luxury Transportation", s_tagline),
         Paragraph(f'<font color="#888888">Invoice # </font><b>{invoice_num}</b>', s_meta_r)],
        [Paragraph("limobluestar1@gmail.com · Available 24/7", s_tagline),
         Paragraph(f'<font color="#888888">Date </font>{generated}', s_meta_r_sm)],
    ], colWidths=[4 * inch, 3 * inch])

    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    story.append(hdr)
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=3, color=GOLD, spaceAfter=25))

    # =========================
    # BILL TO
    # =========================
    story.append(Paragraph("BILL TO", s_section))
    story.append(Paragraph(
        f"<font size=14><b>{trip['first_name']} {trip['last_name']}</b></font>",
        s_body
    ))

    if trip["phone"]:
        story.append(Paragraph(trip["phone"], s_body_muted))

    story.append(Spacer(1, 25))

    # =========================
    # TRIP DETAILS
    # =========================
    story.append(Paragraph("TRIP DETAILS", s_section))

    svc_tbl = Table([
        [Paragraph("DESCRIPTION", s_th),
         Paragraph("DATE", s_th_c),
         Paragraph("AMOUNT", s_th_r)],

        [Paragraph(f"Airport Transfer — {dest_label}", s_td),
         Paragraph(trip["date"], s_td_c),
         Paragraph(f"{trip['price']}", s_td_r)],
    ], colWidths=[3.5 * inch, 1.5 * inch, 2 * inch])

    svc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("BACKGROUND", (0, 1), (-1, -1), CREAM),

        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),

        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),

        ("LINEBELOW", (0, 0), (-1, 0), 2, GOLD),
        ("LINEBELOW", (0, -1), (-1, -1), 1, BORDER),
    ]))

    story.append(svc_tbl)
    story.append(Spacer(1, 25))

    # =========================
    # TOTAL
    # =========================
    tot_tbl = Table([
        ["",
         Paragraph("TOTAL DUE", s_total_lbl),
         Paragraph(f"{trip['price']}", s_total_val)],
    ], colWidths=[3.5 * inch, 1.5 * inch, 2 * inch])

    tot_tbl.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LINEABOVE", (1, 0), (-1, 0), 2, GOLD),
    ]))

    story.append(tot_tbl)
    story.append(Spacer(1, 60))

    # =========================
    # FOOTER
    # =========================
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER, spaceAfter=12))

    story.append(Paragraph(
        "Blue Star Limo LLC · Connecticut’s Premier Luxury Transportation · limobluestar1@gmail.com · Available 24/7",
        s_footer
    ))

    story.append(Paragraph(
        "Thank you for choosing Blue Star Limo — we look forward to serving you.",
        s_footer_i
    ))

    # BUILD PDF
    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"BlueStar-Invoice-{invoice_num}.pdf",
        mimetype="application/pdf"
    )

# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5001)
