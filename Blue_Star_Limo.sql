CREATE TABLE trips (
    id SERIAL PRIMARY KEY,
    date TEXT,
    first_name TEXT,
    last_name TEXT,
    phone TEXT,
    destination TEXT,
    price INTEGER,
    email TEXT
)


SELECT * FROM trips