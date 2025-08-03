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
);

-- If existing table, alter to match (add/drop columns as needed)
ALTER TABLE stock_data ADD COLUMN future_oi_change INTEGER;