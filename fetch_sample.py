from kiteconnect import KiteConnect  # The data fetcher tool
import pandas as pd  # For turning data into easy tables (rows and columns)

# Your API key and today's access token (copy from access_token.txt)
api_key = "m03pvkl6d69rs5g6"  # Replace with your real key
access_token = "QttJK9VOvCRM90FR5BAmbgNokD15aH99"  # Paste the full string from the txt file

# Set up the Kite connection
kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token)

# Fetch the full list of instruments (all stocks, futures, options, etc.)
instruments = kite.instruments()  # This returns a list of dicts
df_instruments = pd.DataFrame(instruments)  # Convert to a DataFrame (table)
print("First 5 rows of instruments data:")
print(df_instruments.head())  # Print sample to terminal
df_instruments.to_csv("instruments.csv", index=False)  # Save to CSV file for later

# Example: Fetch historical data for Reliance (instrument_token from instruments.csv if needed)
reliance_token = 738561  # This is for NSE:RELIANCE - you can change to others
hist = kite.historical_data(instrument_token=reliance_token,
                            from_date="2025-07-31",  # Start date (adjust if needed)
                            to_date="2025-08-02",    # End date (today's date)
                            interval="day")  # Daily candles; try "minute" for intraday
df_hist = pd.DataFrame(hist)  # Convert to table
print("\nHistorical data for Reliance (last few rows):")
print(df_hist.tail())  # Print end of data
df_hist.to_csv("reliance_day.csv", index=False)  # Save to CSV
quote = kite.quote("NSE:RELIANCE")
print("\nLive quote for Reliance:", quote)