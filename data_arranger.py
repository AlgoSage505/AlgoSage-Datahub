import datetime
import time
import sqlite3
import os
import requests
from urllib.parse import urlparse, parse_qs
from kiteconnect import KiteConnect, KiteTicker
from dateutil import tz  # For IST timezone
import pyotp  # For TOTP
from dotenv import load_dotenv  # For .env secrets
import re  # For extracting from error

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
    
    # Add browser disguise (User-Agent)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    })
    
    # Initial GET to set cookies
    initial_response = session.get('https://kite.zerodha.com')
    print("Initial GET status:", initial_response.status_code)  # Debug
    
    # Step 1: POST username/password
    login_payload = {
        "user_id": creds["username"],
        "password": creds["password"],
    }
    login_response = session.post("https://kite.zerodha.com/api/login", data=login_payload)
    
    if login_response.status_code != 200 or login_response.json().get("status") != "success":
        raise ValueError("Login failed: Check username/password. Details: " + login_response.text)
    
    login_data = login_response.json()["data"]
    
    # Step 2: POST TOTP
    totp = pyotp.TOTP(creds["totp_secret"]).now()  # Generate current 6-digit code
    twofa_payload = {
        "user_id": creds["username"],
        "request_id": login_data["request_id"],
        "twofa_value": totp,
        "twofa_type": "totp",
        "skip_session": True,
    }
    twofa_response = session.post("https://kite.zerodha.com/api/twofa", data=twofa_payload)
    
    if twofa_response.status_code != 200 or twofa_response.json().get("status") != "success":
        raise ValueError(f"TOTP failed: Check secret or code: {totp}. Details: " + twofa_response.text)
    
    # Step 3: Get request_token from redirect (let it fail and extract from error)
    kite = KiteConnect(api_key=creds["api_key"])
    login_url = kite.login_url()
    try:
        response = session.get(login_url)
        parsed = urlparse(response.url)
        query_params = parse_qs(parsed.query)
        if "request_token" not in query_params:
            raise ValueError("No request_token in successful response URL.")
        return query_params["request_token"][0]
    except Exception as e:
        # Extract from error message (common in automated login)
        pattern = r"request_token=[A-Za-z0-9]+"
        match = re.search(pattern, str(e))
        if match:
            query_params = parse_qs(match.group(0))
            return query_params["request_token"][0]
        else:
            raise ValueError("No request_token in error message. Check credentials or app settings. Error: " + str(e))

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

# DB connection (using SQLite)
conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# Create table
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

# Full list of scrips from your CSV (all unique names, with exchanges)
scrips = [
    {"name": "SENSEX", "exchange": "BSE"},
    {"name": "NIFTY 50", "exchange": "NSE"},
    {"name": "NIFTY BANK", "exchange": "NSE"},
    {"name": "360ONE", "exchange": "NSE"},
    {"name": "ABB", "exchange": "NSE"},
    {"name": "ABCAPITAL", "exchange": "NSE"},
    {"name": "ABFRL", "exchange": "NSE"},
    {"name": "ADANIENSOL", "exchange": "NSE"},
    {"name": "ADANIENT", "exchange": "NSE"},
    {"name": "ADANIGREEN", "exchange": "NSE"},
    {"name": "ADANIPORTS", "exchange": "NSE"},
    {"name": "ALKEM", "exchange": "NSE"},
    {"name": "AMBER", "exchange": "NSE"},
    {"name": "AMBUJACEM", "exchange": "NSE"},
    {"name": "ANGELONE", "exchange": "NSE"},
    {"name": "APLAPOLLO", "exchange": "NSE"},
    {"name": "APOLLOHOSP", "exchange": "NSE"},
    {"name": "ASHOKLEY", "exchange": "NSE"},
    {"name": "ASIANPAINT", "exchange": "NSE"},
    {"name": "ASTRAL", "exchange": "NSE"},
    {"name": "ATGL", "exchange": "NSE"},
    {"name": "AUBANK", "exchange": "NSE"},
    {"name": "AUROPHARMA", "exchange": "NSE"},
    {"name": "AXISBANK", "exchange": "NSE"},
    {"name": "BAJAJ-AUTO", "exchange": "NSE"},
    {"name": "BAJAJFINSV", "exchange": "NSE"},
    {"name": "BAJFINANCE", "exchange": "NSE"},
    {"name": "BANDHANBNK", "exchange": "NSE"},
    {"name": "BANKBARODA", "exchange": "NSE"},
    {"name": "BANKINDIA", "exchange": "NSE"},
    {"name": "BDL", "exchange": "NSE"},
    {"name": "BEL", "exchange": "NSE"},
    {"name": "BHARATFORG", "exchange": "NSE"},
    {"name": "BHARTIARTL", "exchange": "NSE"},
    {"name": "BHEL", "exchange": "NSE"},
    {"name": "BIOCON", "exchange": "NSE"},
    {"name": "BLUESTARCO", "exchange": "NSE"},
    {"name": "BOSCHLTD", "exchange": "NSE"},
    {"name": "BPCL", "exchange": "NSE"},
    {"name": "BRITANNIA", "exchange": "NSE"},
    {"name": "BSE", "exchange": "NSE"},
    {"name": "CAMS", "exchange": "NSE"},
    {"name": "CANBK", "exchange": "NSE"},
    {"name": "CDSL", "exchange": "NSE"},
    {"name": "CESC", "exchange": "NSE"},
    {"name": "CGPOWER", "exchange": "NSE"},
    {"name": "CHOLAFIN", "exchange": "NSE"},
    {"name": "CIPLA", "exchange": "NSE"},
    {"name": "COALINDIA", "exchange": "NSE"},
    {"name": "COFORGE", "exchange": "NSE"},
    {"name": "COLPAL", "exchange": "NSE"},
    {"name": "CONCOR", "exchange": "NSE"},
    {"name": "CROMPTON", "exchange": "NSE"},
    {"name": "CUMMINSIND", "exchange": "NSE"},
    {"name": "CYIENT", "exchange": "NSE"},
    {"name": "DABUR", "exchange": "NSE"},
    {"name": "DALBHARAT", "exchange": "NSE"},
    {"name": "DELHIVERY", "exchange": "NSE"},
    {"name": "DIVISLAB", "exchange": "NSE"},
    {"name": "DIXON", "exchange": "NSE"},
    {"name": "DLF", "exchange": "NSE"},
    {"name": "DMART", "exchange": "NSE"},
    {"name": "DRREDDY", "exchange": "NSE"},
    {"name": "EICHERMOT", "exchange": "NSE"},
    {"name": "ETERNAL", "exchange": "NSE"},
    {"name": "EXIDEIND", "exchange": "NSE"},
    {"name": "FEDERALBNK", "exchange": "NSE"},
    {"name": "FORTIS", "exchange": "NSE"},
    {"name": "GAIL", "exchange": "NSE"},
    {"name": "GLENMARK", "exchange": "NSE"},
    {"name": "GMRAIRPORT", "exchange": "NSE"},
    {"name": "GODREJCP", "exchange": "NSE"},
    {"name": "GODREJPROP", "exchange": "NSE"},
    {"name": "GRANULES", "exchange": "NSE"},
    {"name": "GRASIM", "exchange": "NSE"},
    {"name": "HAL", "exchange": "NSE"},
    {"name": "HAVELLS", "exchange": "NSE"},
    {"name": "HCLTECH", "exchange": "NSE"},
    {"name": "HDFCAMC", "exchange": "NSE"},
    {"name": "HDFCBANK", "exchange": "NSE"},
    {"name": "HDFCLIFE", "exchange": "NSE"},
    {"name": "HEROMOTOCO", "exchange": "NSE"},
    {"name": "HFCL", "exchange": "NSE"},
    {"name": "HINDALCO", "exchange": "NSE"},
    {"name": "HINDPETRO", "exchange": "NSE"},
    {"name": "HINDUNILVR", "exchange": "NSE"},
    {"name": "HINDZINC", "exchange": "NSE"},
    {"name": "HUDCO", "exchange": "NSE"},
    {"name": "ICICIBANK", "exchange": "NSE"},
    {"name": "ICICIGI", "exchange": "NSE"},
    {"name": "ICICIPRULI", "exchange": "NSE"},
    {"name": "IDEA", "exchange": "NSE"},
    {"name": "IDFCFIRSTB", "exchange": "NSE"},
    {"name": "IEX", "exchange": "NSE"},
    {"name": "IGL", "exchange": "NSE"},
    {"name": "IIFL", "exchange": "NSE"},
    {"name": "INDHOTEL", "exchange": "NSE"},
    {"name": "INDIANB", "exchange": "NSE"},
    {"name": "INDIGO", "exchange": "NSE"},
    {"name": "INDUSINDBK", "exchange": "NSE"},
    {"name": "INDUSTOWER", "exchange": "NSE"},
    {"name": "INFY", "exchange": "NSE"},
    {"name": "INOXWIND", "exchange": "NSE"},
    {"name": "IOC", "exchange": "NSE"},
    {"name": "IRB", "exchange": "NSE"},
    {"name": "IRCTC", "exchange": "NSE"},
    {"name": "IREDA", "exchange": "NSE"},
    {"name": "IRFC", "exchange": "NSE"},
    {"name": "ITC", "exchange": "NSE"},
    {"name": "JINDALSTEL", "exchange": "NSE"},
    {"name": "JIOFIN", "exchange": "NSE"},
    {"name": "JSL", "exchange": "NSE"},
    {"name": "JSWENERGY", "exchange": "NSE"},
    {"name": "JSWSTEEL", "exchange": "NSE"},
    {"name": "JUBLFOOD", "exchange": "NSE"},
    {"name": "KALYANKJIL", "exchange": "NSE"},
    {"name": "KAYNES", "exchange": "NSE"},
    {"name": "KEI", "exchange": "NSE"},
    {"name": "KFINTECH", "exchange": "NSE"},
    {"name": "KOTAKBANK", "exchange": "NSE"},
    {"name": "KPITTECH", "exchange": "NSE"},
    {"name": "LAURUSLABS", "exchange": "NSE"},
    {"name": "LICHSGFIN", "exchange": "NSE"},
    {"name": "LICI", "exchange": "NSE"},
    {"name": "LODHA", "exchange": "NSE"},
    {"name": "LT", "exchange": "NSE"},
    {"name": "LTF", "exchange": "NSE"},
    {"name": "LTIM", "exchange": "NSE"},
    {"name": "LUPIN", "exchange": "NSE"},
    {"name": "M&M", "exchange": "NSE"},
    {"name": "MANAPPURAM", "exchange": "NSE"},
    {"name": "MANKIND", "exchange": "NSE"},
    {"name": "MARICO", "exchange": "NSE"},
    {"name": "MARUTI", "exchange": "NSE"},
    {"name": "MAXHEALTH", "exchange": "NSE"},
    {"name": "MAZDOCK", "exchange": "NSE"},
    {"name": "MCX", "exchange": "NSE"},
    {"name": "MFSL", "exchange": "NSE"},
    {"name": "MOTHERSON", "exchange": "NSE"},
    {"name": "MPHASIS", "exchange": "NSE"},
    {"name": "MUTHOOTFIN", "exchange": "NSE"},
    {"name": "NATIONALUM", "exchange": "NSE"},
    {"name": "NAUKRI", "exchange": "NSE"},
    {"name": "NBCC", "exchange": "NSE"},
    {"name": "NCC", "exchange": "NSE"},
    {"name": "NESTLEIND", "exchange": "NSE"},
    {"name": "NHPC", "exchange": "NSE"},
    {"name": "NMDC", "exchange": "NSE"},
    {"name": "NTPC", "exchange": "NSE"},
    {"name": "NUVAMA", "exchange": "NSE"},
    {"name": "NYKAA", "exchange": "NSE"},
    {"name": "OBEROIRLTY", "exchange": "NSE"},
    {"name": "OFSS", "exchange": "NSE"},
    {"name": "OIL", "exchange": "NSE"},
    {"name": "ONGC", "exchange": "NSE"},
    {"name": "PAGEIND", "exchange": "NSE"},
    {"name": "PATANJALI", "exchange": "NSE"},
    {"name": "PAYTM", "exchange": "NSE"},
    {"name": "PERSISTENT", "exchange": "NSE"},
    {"name": "PETRONET", "exchange": "NSE"},
    {"name": "PFC", "exchange": "NSE"},
    {"name": "PGEL", "exchange": "NSE"},
    {"name": "PHOENIXLTD", "exchange": "NSE"},
    {"name": "PIDILITIND", "exchange": "NSE"},
    {"name": "PIIND", "exchange": "NSE"},
    {"name": "PNB", "exchange": "NSE"},
    {"name": "PNBHOUSING", "exchange": "NSE"},
    {"name": "POLICYBZR", "exchange": "NSE"},
    {"name": "POLYCAB", "exchange": "NSE"},
    {"name": "POONAWALLA", "exchange": "NSE"},
    {"name": "POWERGRID", "exchange": "NSE"},
    {"name": "PPLPHARMA", "exchange": "NSE"},
    {"name": "PRESTIGE", "exchange": "NSE"},
    {"name": "RBLBANK", "exchange": "NSE"},
    {"name": "RECLTD", "exchange": "NSE"},
    {"name": "RELIANCE", "exchange": "NSE"},
    {"name": "RVNL", "exchange": "NSE"},
    {"name": "SAIL", "exchange": "NSE"},
    {"name": "SBICARD", "exchange": "NSE"},
    {"name": "SBILIFE", "exchange": "NSE"},
    {"name": "SBIN", "exchange": "NSE"},
    {"name": "SHREECEM", "exchange": "NSE"},
    {"name": "SHRIRAMFIN", "exchange": "NSE"},
    {"name": "SIEMENS", "exchange": "NSE"},
    {"name": "SJVN", "exchange": "NSE"},
    {"name": "SOLARINDS", "exchange": "NSE"},
    {"name": "SONACOMS", "exchange": "NSE"},
    {"name": "SRF", "exchange": "NSE"},
    {"name": "SUNPHARMA", "exchange": "NSE"},
    {"name": "SUPREMEIND", "exchange": "NSE"},
    {"name": "SUZLON", "exchange": "NSE"},
    {"name": "SYNGENE", "exchange": "NSE"},
    {"name": "TATACHEM", "exchange": "NSE"},
    {"name": "TATACONSUM", "exchange": "NSE"},
    {"name": "TATAELXSI", "exchange": "NSE"},
    {"name": "TATAMOTORS", "exchange": "NSE"},
    {"name": "TATAPOWER", "exchange": "NSE"},
    {"name": "TATASTEEL", "exchange": "NSE"},
    {"name": "TATATECH", "exchange": "NSE"},
    {"name": "TCS", "exchange": "NSE"},
    {"name": "TECHM", "exchange": "NSE"},
    {"name": "TIINDIA", "exchange": "NSE"},
    {"name": "TITAGARH", "exchange": "NSE"},
    {"name": "TITAN", "exchange": "NSE"},
    {"name": "TORNTPHARM", "exchange": "NSE"},
    {"name": "TORNTPOWER", "exchange": "NSE"},
    {"name": "TRENT", "exchange": "NSE"},
    {"name": "TVSMOTOR", "exchange": "NSE"},
    {"name": "ULTRACEMCO", "exchange": "NSE"},
    {"name": "UNIONBANK", "exchange": "NSE"},
    {"name": "UNITDSPR", "exchange": "NSE"},
    {"name": "UNOMINDA", "exchange": "NSE"},
    {"name": "UPL", "exchange": "NSE"},
    {"name": "VBL", "exchange": "NSE"},
    {"name": "VEDL", "exchange": "NSE"},
    {"name": "VOLTAS", "exchange": "NSE"},
    {"name": "WIPRO", "exchange": "NSE"},
    {"name": "YESBANK", "exchange": "NSE"},
    {"name": "ZYDUSLIFE", "exchange": "NSE"}
]

# Symbol mappings for indices
symbol_map = {
    "NIFTY 50": {"spot_symbol": "NIFTY50", "future_name": "NIFTY"},
    "NIFTY BANK": {"spot_symbol": "BANKNIFTY", "future_name": "BANKNIFTY"},
    "SENSEX": {"spot_symbol": "SENSEX", "future_name": "SENSEX"}
}

# Get immediate future
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
    spot_instrument = f"{exch}:{spot_symbol.replace(' ', '%20')}"
    
    fut_exchange = 'BFO' if name == 'SENSEX' else 'NFO'
    future_name = symbol_map.get(name, {"future_name": name})['future_name']
    future_instrument = get_immediate_future(future_name, fut_exchange)
    if future_instrument:
        instrument_list.append(future_instrument)
        future_oi_tracker[future_instrument] = 0
    instrument_list.append(spot_instrument)

# Fetch and store
def fetch_and_store():
    data_rows = []
    quotes = {}
    
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
    
    cursor.executemany("""
        INSERT INTO stock_data (timestamp, stock_index_name, exchange, pct_chng, day_open, prev_day_close, ltp, future_ltp, future_oi, future_oi_change)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_rows)
    conn.commit()
    print("Data stored successfully.")

# Websocket
def setup_websocket():
    kws = KiteTicker(credentials["api_key"], access_token)
    
    def on_ticks(ws, ticks):
        for tick in ticks:
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
    
    kws.connect(threaded=True)

# Scan
def scan_at_955():
    ist = datetime.datetime.now(tz.gettz('Asia/Kolkata'))
    if ist.hour == 9 and ist.minute == 55:
        fetch_and_store()
        cursor.execute("SELECT * FROM stock_data ORDER BY timestamp DESC LIMIT ?", (len(scrips),))
        latest_data = cursor.fetchall()
        
        filtered_stocks = []
        for row in latest_data:
            name = row[1]
            pct_chng = row[3]
            prev_close = row[5]
            if name not in ["SENSEX", "NIFTY 50", "NIFTY BANK"] and abs(pct_chng) > 2 and 250 <= prev_close <= 3500:
                filtered_stocks.append((name, pct_chng))
        
        top_10 = sorted(filtered_stocks, key=lambda x: abs(x[1]), reverse=True)[:10]
        print("Filtered Stocks (>2% change, 250-3500 price):", [s[0] for s in filtered_stocks])
        print("Top 10 Highlighted:", [s[0] for s in top_10])

# Main
setup_websocket()
while True:
    ist_now = datetime.datetime.now(tz.gettz('Asia/Kolkata'))
    if 9 <= ist_now.hour <= 15:
        fetch_and_store()
        scan_at_955()
    time.sleep(300)