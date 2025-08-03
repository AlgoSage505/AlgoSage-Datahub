import datetime
import time
import sqlite3
import os
import requests
import re
from urllib.parse import urlparse, parse_qs
from kiteconnect import KiteConnect, KiteTicker
from dateutil import tz  # For IST timezone
import pyotp  # For TOTP
from dotenv import load_dotenv  # For .env secrets

# Load secrets from .env
load_dotenv()

credentials = {
    "username": os.getenv("ZERODHA_USERNAME"),
    "password": os.getenv("ZERODHA_PASSWORD"),
    "totp_secret": os.getenv("ZERODHA_TOTP_SECRET"),
    "api_key": os.getenv("ZERODHA_API_KEY"),
    "api_secret": os.getenv("ZERODHA_API_SECRET"),
}

# Function to automate login and get request_token
def get_request_token(creds):
    session = requests.Session()
    kite = KiteConnect(api_key=creds["api_key"])
    
    # Step 1: Get login page (to set cookies)
    session.get(kite.login_url())
    
    # Step 2: POST username/password
    login_payload = {
        "user_id": creds["username"],
        "password": creds["password"],
    }
    login_response = session.post("https://kite.zerodha.com/api/login", data=login_payload)
    
    if login_response.status_code != 200 or "success" not in login_response.json().get("status", ""):
        raise ValueError("Login failed: Check username/password.")
    
    login_data = login_response.json()["data"]
    
    # Step 3: POST TOTP
    totp = pyotp.TOTP(creds["totp_secret"]).now()  # Generate current 6-digit code
    twofa_payload = {
        "user_id": creds["username"],
        "request_id": login_data["request_id"],
        "twofa_value": totp,
        "twofa_type": "totp",
    }
    twofa_response = session.post("https://kite.zerodha.com/api/twofa", data=twofa_payload)
    
    if twofa_response.status_code != 200 or "success" not in twofa_response.json().get("status", ""):
        raise ValueError(f"TOTP failed: Check secret or code: {totp}")
    
    # Step 4: Get request_token from redirect
    response = session.get(kite.login_url())
    parsed = urlparse(response.url)
    if parsed.hostname != "127.0.0.1":  # Expected redirect
        raise ValueError("Unexpected redirect URL.")
    
    query_params = parse_qs(parsed.query)
    if "request_token" not in query_params:
        raise ValueError("No request_token in URL.")
    
    return query_params["request_token"][0]

# Generate access_token automatically
try:
    request_token = get_request_token(credentials)
    kite = KiteConnect(api_key=credentials["api_key"])
    data = kite.generate_session(request_token, api_secret=credentials["api_secret"])
    access_token = data["access_token"]
    kite.set_access_token(access_token)
    print("Access token generated automatically:", access_token)
except Exception as e:
    print("Error generating token:", e)
    exit(1)  # Stop if fails

# Now the rest of your script...

# DB connection (using SQLite - simple file-based)
conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS stock_data (
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    stock_index_name TEXT,
    exchange TEXT,
    pct_chng REAL,
    day_open REAL,
    prev_day_close REAL,
    ltp REAL,
    future_ltp REAL,
    future_oi INTEGER,
    future_oi_change INTEGER
)
""")
conn.commit()

# List of scrips from CSV (add all ~250 here)
scrips = [
    {"name": "SENSEX", "exchange": "BSE"},
    {"name": "NIFTY 50", "exchange": "NSE"},
    {"name": "NIFTY BANK", "exchange": "NSE"},
    {"name": "360ONE", "exchange": "NSE"},
    {"name": "ABB", "exchange": "NSE"},
    # ... Add the full list, e.g.:
    {"name": "ZYDUSLIFE", "exchange": "NSE"}
    # Paste all from your CSV, like {"name": "ABCAPITAL", "exchange": "NSE"}, etc.
]

# Symbol mappings for indices
symbol_map = {
    "NIFTY 50": {"spot_symbol": "NIFTY 50", "future_name": "NIFTY"},
    "NIFTY BANK": {"spot_symbol": "BANKNIFTY", "future_name": "BANKNIFTY"},
    "SENSEX": {"spot_symbol": "SENSEX", "future_name": "SENSEX"}
}

# Function to get immediate future instrument
def get_immediate_future(base_name, fut_exchange):
    try:
        instruments = kite.instruments()
        today = datetime.date.today()
        futures = [i for i in instruments if i['name'].upper() == base_name.upper() and
                   i['instrument_type'] == 'FUT' and
                   i['exchange'] == fut_exchange and
                   i['expiry'] >= today]
        if not futures:
            return None
        nearest = min(futures, key=lambda x: x['expiry'])
        return f"{nearest['exchange']}:{nearest['tradingsymbol']}"
    except Exception as e:
        print(f"Error getting future for {base_name}: {e}")
        return None

# Prepare instruments
instrument_list = []
future_oi_tracker = {}
for scrip in scrips:
    name = scrip['name']
    exch = scrip['exchange']
    spot_symbol = symbol_map.get(name, {"spot_symbol": name})['spot_symbol']
    spot_instrument = f"{exch}:{spot_symbol.replace(' ', '%20')}"  # URL encode spaces
    
    fut_exchange = 'BFO' if name == 'SENSEX' else 'NFO'
    future_name = symbol_map.get(name, {"future_name": name})['future_name']
    future_instrument = get_immediate_future(future_name, fut_exchange)
    if future_instrument:
        instrument_list.append(future_instrument)
        future_oi_tracker[future_instrument] = 0
    instrument_list.append(spot_instrument)

# Function to fetch and store data
def fetch_and_store():
    data_rows = []
    quotes = {}
    
    # Batch fetch (max 500 per call, we use 250 safe)
    for i in range(0, len(instrument_list), 250):
        batch = instrument_list[i:i+250]
        try:
            quotes.update(kite.quote(batch))
        except Exception as e:
            print(f"Quote error: {e}")
    
    current_time = datetime.datetime.now(tz.gettz('Asia/Kolkata'))
    
    for scrip in scrips:
        name = scrip['name']
        exch = scrip['exchange']
        spot_symbol = symbol_map.get(name, {"spot_symbol": name})['spot_symbol']
        spot_instrument = f"{exch}:{spot_symbol.replace(' ', '%20')}"
        future_name = symbol_map.get(name, {"future_name": name})['future_name']
        future_instrument = get_immediate_future(future_name, 'BFO' if name == 'SENSEX' else 'NFO')
        
        spot_data = quotes.get(spot_instrument, {})
        future_data = quotes.get(future_instrument, {}) if future_instrument else {}
        
        ltp = spot_data.get('last_price', 0)
        day_open = spot_data.get('ohlc', {}).get('open', 0)
        prev_close = spot_data.get('ohlc', {}).get('close', 0)
        pct_chng = ((ltp - prev_close) / prev_close * 100) if prev_close else 0
        
        future_ltp = future_data.get('last_price', 0)
        future_oi = future_data.get('oi', 0)
        
        oi_change = future_oi - future_oi_tracker.get(future_instrument, 0)
        future_oi_tracker[future_instrument] = future_oi
        
        row = (str(current_time), name, exch, pct_chng, day_open, prev_close, ltp, future_ltp, future_oi, oi_change)
        data_rows.append(row)
    
    # Batch insert
    cursor.executemany("""
        INSERT INTO stock_data (timestamp, stock_index_name, exchange, pct_chng, day_open, prev_day_close, ltp, future_ltp, future_oi, future_oi_change)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_rows)
    conn.commit()
    print("Data stored successfully.")

# Websocket setup with error handling
def setup_websocket():
    kws = KiteTicker(credentials["api_key"], access_token)
    
    def on_ticks(ws, ticks):
        for tick in ticks:
            # Update LTP etc.
            print(f"Tick: {tick['instrument_token']} LTP = {tick.get('last_price')}")
    
    def on_connect(ws, response):
        tokens = [int(kite.ltp(i).get(i, {}).get('instrument_token', 0)) for i in instrument_list if kite.ltp(i).get(i)]
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)
        print("Websocket connected.")
    
    def on_error(ws, code, reason):
        print(f"Websocket error: {code} - {reason}")
    
    def on_close(ws, code, reason):
        print(f"Websocket closed: {code} - {reason}. Reconnecting...")
        time.sleep(5)
        ws.connect()
    
    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_error = on_error
    kws.on_close = on_close
    
    kws.connect(threaded=True)  # Run in background

# Scanning at 9:55 IST
def scan_at_955():
    ist = datetime.datetime.now(tz.gettz('Asia/Kolkata'))
    if ist.hour == 9 and ist.minute == 55:
        fetch_and_store()
        cursor.execute("SELECT * FROM stock_data ORDER BY timestamp DESC LIMIT ?", (len(scrips),))
        latest_data = cursor.fetchall()
        
        filtered_stocks = []
        for row in latest_data:
            # Unpack: adjust based on columns (timestamp is 0, name 1, etc.)
            name = row[1]
            pct_chng = row[3]
            prev_close = row[5]
            if name not in ["SENSEX", "NIFTY 50", "NIFTY BANK"] and abs(pct_chng) > 2 and 250 <= prev_close <= 3500:
                filtered_stocks.append((name, pct_chng))
        
        top_10 = sorted(filtered_stocks, key=lambda x: abs(x[1]), reverse=True)[:10]
        print("Filtered Stocks (>2% change, 250-3500 price):", [s[0] for s in filtered_stocks])
        print("Top 10 Highlighted:", [s[0] for s in top_10])

# Main loop
setup_websocket()
while True:
    ist_now = datetime.datetime.now(tz.gettz('Asia/Kolkata'))
    if 9 <= ist_now.hour <= 15:  # Approx market hours
        fetch_and_store()
        scan_at_955()
    time.sleep(300)  # Poll every 5 min