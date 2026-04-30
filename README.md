Blue Star Limo — Booking and Admin System
Overview

Blue Star Limo is a full-stack web application designed for a limousine service business. The application allows customers to submit booking requests online, stores trip data in a database, and provides an administrative dashboard for managing bookings.

This project was developed as a semester-long assignment to demonstrate practical web development concepts, including frontend design, backend API development, and database integration.

Features
Customer Functionality
Submit ride booking requests through a web form
Select destinations (e.g., JFK, LGA, HVN)
Provide contact and trip details
Receive a confirmation after submission
Administrative Dashboard
View all submitted bookings
Filter trips by destination
Delete bookings
View summary statistics such as total trips and revenue
Invoicing
Generate PDF invoices for bookings
Display customer details, trip information, and pricing
Technology Stack
Backend
Python
Flask
Flask-CORS
Frontend
HTML
CSS
JavaScript
Database
PostgreSQL
Libraries
psycopg2 (PostgreSQL connection)
reportlab (PDF generation)
python-dotenv (environment variable management)
Project Structure
Blue_Star_Limo/
│
├── app.py              # Flask application and API routes
├── templates/          # HTML pages (index, contact, admin, etc.)
├── static/             # CSS, JavaScript, and image assets
├── README.md
Setup Instructions
1. Clone the Repository
git clone https://github.com/YOUR_USERNAME/Blue_Star_Limo.git
cd Blue_Star_Limo
2. Install Dependencies

Ensure Python 3.9 or later is installed, then run:

pip install flask flask-cors psycopg2-binary reportlab python-dotenv
3. Configure Environment Variables

Create a .env file in the project root directory:

DB_PASSWORD=your_postgres_password
4. Run the Application
python app.py
5. Access the Application

Open a browser and navigate to:

http://127.0.0.1:5001/
API Endpoints
Method	Endpoint	Description
GET	/api/trips	Retrieve all bookings
GET	/api/trips/	Retrieve bookings filtered by destination
POST	/api/book	Create a new booking
DELETE	/api/delete/	Delete a booking
Assumptions and Requirements
Basic familiarity with Python and Flask is assumed
PostgreSQL must be installed and running locally
Environment variables must be configured before running the application
The application is intended for local development but can be extended for deployment
Future Improvements
Implement secure authentication for the admin dashboard
Add email confirmation for bookings
Deploy the application to a cloud platform (e.g., Railway or Render)
Improve mobile responsiveness and user interface
Author

Nicky Desai
Blue Star Limo Project