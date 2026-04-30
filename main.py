# import psycopg2
# import os

# conn = psycopg2.connect(
#     dbname="bluestar_limo",
#     user="postgres",
#     password=os.environ.get("DB_PASSWORD"),
#     host="localhost",
#     port="5432"
# )
# cursor = conn.cursor()

# print("1. Add New Trip")
# print("2. View All Trips")
# print("3. Search Trips By First Name")
# print("4. Search Trips By Destination (Admin)")

# choice = input("Choose an option (1 2 3 or 4): ")

# if choice == "1":
#     date = input("Enter trip date (MM/DD/YYYY): ")
#     first_name = input("Enter first name: ")
#     last_name = input("Enter last name: ")
#     phone = input("Enter phone number: ")
#     destination = input("Enter destination: ")

#     price = "$0"

#     cursor.execute("""
#     INSERT INTO Trips 
#     (Dates, "First Name", "Last Name", "Phone Number", Destination, Price)
#     VALUES (?, ?, ?, ?, ?, ?)
#     """, (date, first_name, last_name, phone, destination, price))

#     conn.commit()
#     print("Trip successfully added. Price will be assigned by admin.")

# elif choice == "2":
#     cursor.execute("SELECT * FROM Trips")
#     rows = cursor.fetchall()

#     if rows:
#         for row in rows:
#             print("\n-----------------------------")
#             print(f"Trip ID: {row[0]}")
#             print(f"Date: {row[1]}")
#             print(f"Name: {row[2]} {row[3]}")
#             print(f"Phone: {row[4]}")
#             print(f"Destination: {row[5]}")
#             print(f"Price: {row[6]}")
#         print("-----------------------------")
#     else:
#         print("No trips found.")

# elif choice == "3":
#     search_name = input("Enter first name to search: ")

#     cursor.execute("""
#     SELECT * FROM Trips
#     WHERE "First Name" = ?
#     """, (search_name,))

#     rows = cursor.fetchall()

#     if rows:
#         print("\nReservations Found:\n")
#         for row in rows:
#             print("\n-----------------------------")
#             print(f"Trip ID: {row[0]}")
#             print(f"Date: {row[1]}")
#             print(f"Name: {row[2]} {row[3]}")
#             print(f"Phone: {row[4]}")
#             print(f"Destination: {row[5]}")
#             print(f"Price: {row[6]}")
#         print("-----------------------------")
#     else:
#         print("No reservations found for that name.")

# elif choice == "4":
#     destination_search = input("Enter destination to search : ")

#     cursor.execute("""
#     SELECT * FROM Trips
#     WHERE Destination = ?
#     """, (destination_search,))

#     rows = cursor.fetchall()

#     if rows:
#         print(f"\nTrips Going to {destination_search}:\n")
#         for row in rows:
#             print("\n-----------------------------")
#             print(f"Trip ID: {row[0]}")
#             print(f"Date: {row[1]}")
#             print(f"Name: {row[2]} {row[3]}")
#             print(f"Phone: {row[4]}")
#             print(f"Destination: {row[5]}")
#             print(f"Price: {row[6]}")
#         print("-----------------------------")
#     else:
#         print(f"No trips found to {destination_search}.")


# else:
#     print("Invalid option.")

# conn.close()