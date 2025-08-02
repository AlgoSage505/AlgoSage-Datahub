# file: new_sell_engine.py
import math
import pandas as pd
from datetime import datetime, timedelta
import numpy as np  # For ATR calc

def mround(x, base=0.25):
    return round(base * round(float(x) / base), 2) if base else round(x, 2)

def theory1_upside(price):
    g93 = (math.sqrt(price) + 2) ** 2
    step = (g93 - price) / 24
    degrees = [15, 30, 45, 90, 135, 180, 225, 270, 315]
    return [mround(price + (step * (d / 15))) for d in degrees]

def theory1_downside(price):
    m93 = (math.sqrt(price) - 2) ** 2
    step = (price - m93) / 24
    degrees = [15, 30, 45, 90, 135, 180, 225, 270, 315]
    return [mround(price - (step * (d / 15))) for d in degrees]

def theory2_short(price):  # Short-term theory (AP-based, narrower)
    sqrt_price = math.sqrt(price)
    ap19 = int(sqrt_price)
    ap11 = ap19 + 1
    step = (ap11 - ap19) / 8
    vals = [ap11 - i * step for i in range(9)]
    return [round(v ** 2, 2) for v in vals]

def theory2_long(price):  # Long-term theory (AO-based, wider)
    sqrt_price = math.sqrt(price)
    ap19 = int(sqrt_price)
    ap11 = ap19 + 1
    ao11 = ap11 + 1
    ao19 = ap19 - 1
    step = (ao11 - ao19) / 8
    vals = [ao11 - i * step for i in range(9)]
    return [round(v ** 2, 2) for v in vals]

def build_w_index(price):
    j_levels = theory1_upside(price)
    k_levels = theory1_downside(price)
    l_levels = theory2_long(price)  # Wider for Long-Term (L)
    m_levels = theory2_short(price)  # Narrower for Short-Term (M)
    return pd.DataFrame({
        'Upside (J)': j_levels,
        'Downside (K)': k_levels,
        'Long-Term (L)': l_levels,
        'Short-Term (M)': m_levels
    })

def generate_mock_prices(trigger_level, target_1, level_270, max_extreme, scenario="Reach_270_Then_Retrace", num_bars=20, start_time=datetime.now(), direction="down"):
    start_price = trigger_level + 1.0
    post_level_inc = -0.1
    retrace_inc = 1.5
    prices = []
    times = []
    current_price = start_price
    current_time = start_time
    increment = 0.0

    for i in range(num_bars):
        if i < 5:
            if i == 0:
                target_for_segment = trigger_level - 2.0
                increment = (target_for_segment - current_price) / 5
            current_price += increment
        elif 5 <= i < 10:
            if i == 5:
                target_for_segment = target_1 - 2.0
                increment = (target_for_segment - current_price) / 5
            current_price += increment
        elif 10 <= i < 15:
            if i == 10:
                target_for_segment = level_270 + 1.0
                increment = (target_for_segment - current_price) / 5
            current_price += increment
        elif i == 15:
            current_price = level_270
        elif 15 < i <= 17:
            current_price += post_level_inc
        else:
            current_price += retrace_inc

        prices.append(round(current_price, 2))
        times.append(current_time)
        current_time += timedelta(minutes=1)

    # For ATR mock, add simulated high/low/close (price + noise)
    df = pd.DataFrame({'time': times, 'price': prices})
    df['high'] = df['price'] + np.random.uniform(0, 1, len(df))  # Simulated high
    df['low'] = df['price'] - np.random.uniform(0, 1, len(df))  # Simulated low
    df['close'] = df['price']
    return df

def calculate_atr(price_df, period=15):
    if len(price_df) < period:
        return 0
    df = price_df.tail(period + 1)
    high = df['high']
    low = df['low']
    close = df['close']
    prev_close = close.shift(1)
    tr = np.maximum(high - low, np.maximum(abs(high - prev_close), abs(low - prev_close)))
    atr = tr.rolling(window=period).mean().iloc[-1]
    return atr if not np.isnan(atr) else 0

def get_atr_config(price):
    configs = {
        (200, 599): {'sl_mult': 2.0},
        (600, 700): {'sl_mult': 1.8},
        (701, 1000): {'sl_mult': 1.6},
        (1001, 1499): {'sl_mult': 1.5},
        (1500, 2000): {'sl_mult': 1.4},
        (2001, 4000): {'sl_mult': 1.2},
        (20000, 40000): {'sl_mult': 1.1},  # NIFTY 50 and NIFTY 50 FUTURES
        (40000, 70000): {'sl_mult': 1.0},  # NIFTY BANK and BANKNIFTY FUTURES
        (70000, 100000): {'sl_mult': 1.0},  # SENSEX and SENSEX FUTURES
    }
    for range_min, range_max in configs:
        if range_min <= price <= range_max:
            return configs[(range_min, range_max)]
    return {'sl_mult': 1.5}  # Default for other prices

def sustained_below(df, level, required_minutes=5):
    count = 0
    for idx, row in df.iterrows():
        if row['price'] <= level:
            count += 1
            if count >= required_minutes:
                return idx
        else:
            count = 0
    return None

def run_sell_engine(w_index_df, price_df, qty=200, frozen_price=0, sustainability_minutes=5):
    atr = calculate_atr(price_df)
    config = get_atr_config(frozen_price)
    sl_mult = config['sl_mult']
    trigger_level = w_index_df['Downside (K)'][0]
    if trigger_level >= frozen_price:
        print("No valid trigger level below CMP; skipping sell")
        return
    target_1 = min(w_index_df['Downside (K)'][1], w_index_df['Short-Term (M)'][4])
    if trigger_level <= target_1:
        print("Skip sell: Trigger <= T1 (illogical setup)")
        return
    min_gap_pct = 0.003
    gap_pct = (trigger_level - target_1) / trigger_level
    if gap_pct < min_gap_pct:
        print(f"Skip sell: Gap between trigger ({trigger_level}) and T1 ({target_1}) is {gap_pct*100:.2f}%, less than 0.3%")
        return
    sl_candidates = [
        w_index_df['Upside (J)'][0],
        w_index_df['Short-Term (M)'][2]
    ]
    entry_idx = sustained_below(price_df.copy(), trigger_level, sustainability_minutes)
    if entry_idx is None:
        print("No sell trigger: Price did not sustain below trigger level for at least 5 minutes")
        return
    entry_price = price_df.iloc[entry_idx]['price']
    gap_pct_entry = (entry_price - target_1) / entry_price
    if gap_pct_entry < min_gap_pct:
        print(f"Skip sell: Gap between entry ({entry_price}) and T1 ({target_1}) is {gap_pct_entry*100:.2f}%, less than 0.3%")
        return
    sl_above = [c for c in sl_candidates if c > entry_price]
    if not sl_above:
        print("No valid SL above entry; skipping sell")
        return
    base_first_sl = min(sl_above)
    first_sl = base_first_sl + (atr * sl_mult)
    lowest_price = entry_price
    t1_hit = False
    remaining_qty = qty
    base_sl = first_sl
    base_price = entry_price
    current_sl = base_sl
    max_downside = w_index_df['Downside (K)'][8]
    print(f"\n✅ SELL ENTRY at {entry_price} (Qty: {qty}, Time: {price_df.iloc[entry_idx]['time']})")
    print(f"🎯 T1: {target_1}, T2: OPEN, Max Downside: {max_downside}")
    print(f"🛡 SL1: {current_sl}")
    for i in range(entry_idx + 1, len(price_df)):
        price = price_df.iloc[i]['price']
        time = price_df.iloc[i]['time']
        if price >= current_sl:
            print(f"🛑 SL HIT at {price} (Time: {time}, Remaining Qty: {remaining_qty} exited)")
            break
        if price <= max_downside:
            print(f"🛑 MAX DOWNSIDE at {price} (Time: {time}, Remaining Qty: {remaining_qty} exited)")
            break
        if price < lowest_price:
            lowest_price = price
            new_sl = base_sl - (base_price - lowest_price)
            if new_sl < current_sl:
                current_sl = new_sl
                print(f"🔄 Trailed SL to {current_sl:.2f} (Price: {price}, Time: {time})")
        if not t1_hit and price <= target_1:
            t1_hit = True
            book_qty = remaining_qty // 2
            remaining_qty -= book_qty
            base_sl2 = min(w_index_df['Downside (K)'][0], entry_price - 1)
            sl2 = base_sl2 + (atr * sl_mult)
            current_sl = sl2
            lowest_price = price
            base_sl = sl2
            base_price = target_1
            print(f"🎯 T1 HIT at {price} (Time: {time}, Booked {book_qty} qty, Remaining: {remaining_qty})")
            print(f"🛡 SL2: {current_sl:.2f}")
    print("\n📋 SUMMARY")
    print(f"Entry: {entry_price}, Final SL: {current_sl:.2f}, T1 Hit: {t1_hit}")

# Example usage
if __name__ == "__main__":
    price = float(input("Enter price: ") or 2380)
    sustainability_minutes = 5

    w_df = build_w_index(price)
    print(w_df)

    trigger_level = w_df['Downside (K)'][0]
    target_1 = min(w_df['Downside (K)'][1], w_df['Short-Term (M)'][4])
    level_270 = w_df['Downside (K)'][7]
    max_extreme = w_df['Downside (K)'][8]
    mock_df = generate_mock_prices(trigger_level, target_1, level_270, max_extreme, direction="down")
    run_sell_engine(w_df, mock_df, frozen_price=price, sustainability_minutes=sustainability_minutes)