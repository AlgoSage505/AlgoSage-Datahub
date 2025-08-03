from kiteconnect import KiteConnect
import psycopg2

# Kite setup
api_key = "m03pvkl6d69rs5g6"
access_token = "QttJK9VOvCRM90FR5BAmbgNokD15aH99"  # From authenticate.py

kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

# Fetch historical
reliance_token = 738561
hist = kite.historical_data(instrument_token=reliance_token, from_date="2025-07-01", to_date="2025-08-03", interval="day")

# DB connect
conn = psycopg2.connect(dbname="postgres", user="postgres", password="alok505", host="localhost")
cur = conn.cursor()

# Insert (loop over records)
for record in hist:
    cur.execute("""
        INSERT INTO historical (time, instrument_token, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (record['date'], reliance_token, record['open'], record['high'], record['low'], record['close'], record['volume']))

conn.commit()
print("Data inserted successfully!")
cur.close()
conn.close()