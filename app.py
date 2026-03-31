from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)  # ✅ This fixes your issue


# Home route (API landing page)
@app.route("/")
def home():
    return """
    <h1>Blue Star Limo Booking API</h1>
    <p>This API handles bookings for the Blue Star Limo website.</p>

    <h3>Available Endpoints:</h3>
    <ul>
        <li><a href="/api/trips">View All Trips</a></li>
    </ul>
    """


# GET endpoint - return all trips
@app.route("/api/trips", methods=["GET"])
def get_trips():

    conn = sqlite3.connect("BlueStarLimo.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM Trips ORDER BY Id DESC")
    rows = cursor.fetchall()

    conn.close()

    trips = []

    for row in rows:
        trip = {
            "id": row[0],
            "date": row[1],
            "first_name": row[2],
            "last_name": row[3],
            "phone": row[4],
            "destination": row[5],
            "price": row[6]
        }
        trips.append(trip)

    return jsonify(trips)


# POST endpoint - create booking
@app.route("/api/book", methods=["POST"])
def create_booking():

    date = request.form["date"]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    phone = request.form["phone"]
    destination = request.form["destination"]

    price = "$0"

    conn = sqlite3.connect("BlueStarLimo.db")
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO Trips (Dates, "First Name", "Last Name", "Phone Number", Destination, Price)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (date, first_name, last_name, phone, destination, price))

    conn.commit()
    conn.close()

    return """
    <h2>Booking Successfully Created!</h2>
    <p>Your trip has been added to the system.</p>
    <a href="http://127.0.0.1:5500/contact.html">Book Another Trip</a>
    """


if __name__ == "__main__":
    app.run(debug=True, port=5001)