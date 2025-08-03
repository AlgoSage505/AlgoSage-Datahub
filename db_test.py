import psycopg2  # DB connector
# Connect (use your password)
conn = psycopg2.connect(dbname="postgres", user="postgres", password="alok505", host="localhost")
cur = conn.cursor()
cur.execute("SELECT version();")  # Test query
print("DB Version:", cur.fetchone())  # Prints PostgreSQL info
cur.close()
conn.close()