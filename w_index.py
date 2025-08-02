import math
import pandas as pd
from datetime import datetime, timedelta

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

def generate_mock_prices(trigger_level, target_1, target_2, num_bars=20, start_time=datetime.now()):
    start_price = trigger_level - 1.0
    prices = []
    times = []
    current_price = start_price
    current_time = start_time
    for _ in range(num_bars):
        current_price += math.sin(_) * 5 + (_ / 10)
        prices.append(round(current_price, 2))
        times.append(current_time)
        current_time += timedelta(minutes=1)
    return pd.DataFrame({'time': times, 'price': prices})

def sustained_above(df, level, required_min=5):
    df.set_index('time', inplace=True)
    resampled = df.resample('5min').last()
    df.reset_index(inplace=True)
    resampled.reset_index(inplace=True)
    count = 0
    for i, row in resampled.iterrows():
        if row['price'] >= level:
            count += 1
            if count >= (required_min // 5):
                return i
        else:
            count = 0
    return None

def run_buy_engine(w_index_df, price_df, qty=200, frozen_price=0):
    # Trigger candidates: J12, L16, L17, M17, M16, M15
    trigger_candidates = [
        w_index_df['Upside (J)'][0],
        w_index_df['Long-Term (L)'][3],
        w_index_df['Long-Term (L)'][4],
        w_index_df['Short-Term (M)'][4],
        w_index_df['Short-Term (M)'][3],
        w_index_df['Short-Term (M)'][2]
    ]
    # Dynamic: Min above frozen_price for first breakout
    candidates_above = [c for c in trigger_candidates if c > frozen_price]
    if not candidates_above:
        print("No valid trigger levels above CMP; skipping buy")
        return
    trigger_level = min(candidates_above)

    target_1 = w_index_df['Upside (J)'][1]
    if trigger_level >= target_1:
        print("Skip buy: Trigger >= T1 (illogical setup)")
        return

    target_2 = max(w_index_df['Upside (J)'][2], w_index_df['Long-Term (L)'][4])  # J14 and L17 (mid long-term)

    # SL candidates: K12, M15, M16, M17 (narrow short-term)
    sl_candidates = [
        w_index_df['Downside (K)'][0],
        w_index_df['Short-Term (M)'][2],
        w_index_df['Short-Term (M)'][3],
        w_index_df['Short-Term (M)'][4]
    ]

    entry_idx = sustained_above(price_df.copy(), trigger_level)
    if entry_idx is None:
        print("No buy trigger")
        return

    entry_price = price_df.iloc[entry_idx]['price']

    # Dynamic SL1: Max below entry
    sl_below = [c for c in sl_candidates if c < entry_price]
    if not sl_below:
        print("No valid SL below entry; skipping buy")
        return
    first_sl = max(sl_below)

    highest_price = entry_price
    t1_hit = False
    remaining_qty = qty
    base_sl = first_sl
    base_price = entry_price
    current_sl = base_sl

    print(f"\n✅ BUY ENTRY at {entry_price} (Qty: {qty}, Time: {price_df.iloc[entry_idx]['time']})")
    print(f"🎯 T1: {target_1}, T2: {target_2}")
    print(f"🛡 SL1: {current_sl}")

    for i in range(entry_idx + 1, len(price_df)):
        price = price_df.iloc[i]['price']
        time = price_df.iloc[i]['time']

        if price <= current_sl:
            print(f"🛑 SL HIT at {price} (Time: {time}, Remaining Qty: {remaining_qty} exited)")
            break

        if price > highest_price:
            highest_price = price
            new_sl = base_sl + (highest_price - base_price)
            if new_sl > current_sl:
                current_sl = new_sl
                print(f"🔄 Trailed SL to {current_sl:.2f} (Price: {price}, Time: {time})")

        if not t1_hit and price >= target_1:
            t1_hit = True
            book_qty = remaining_qty // 2
            remaining_qty -= book_qty
            sl2 = max(entry_price + 1, trigger_level)
            current_sl = sl2
            highest_price = price
            base_sl = sl2
            base_price = target_1
            print(f"🎯 T1 HIT at {price} (Time: {time}, Booked {book_qty} qty, Remaining: {remaining_qty})")
            print(f"🛡 SL2: {current_sl:.2f}")

        if t1_hit and price >= target_2:
            print(f"🎯 T2 HIT at {price} (Time: {time}, Exited remaining {remaining_qty})")
            break

    print("\n📋 SUMMARY")
    print(f"Entry: {entry_price}, Final SL: {current_sl:.2f}, T1 Hit: {t1_hit}")

# Example usage
if __name__ == "__main__":
    price = float(input("Enter price: ") or 2380)
    w_df = build_w_index(price)
    print(w_df)
    
    trigger_candidates = [
        w_df['Upside (J)'][0],
        w_df['Long-Term (L)'][3],
        w_df['Long-Term (L)'][4],
        w_df['Short-Term (M)'][4],
        w_df['Short-Term (M)'][3],
        w_df['Short-Term (M)'][2]
    ]
    candidates_above = [c for c in trigger_candidates if c > price]
    trigger_level = min(candidates_above) if candidates_above else price + 1  # Fallback
    target_1 = w_df['Upside (J)'][1]
    target_2 = max(w_df['Upside (J)'][2], w_df['Long-Term (L)'][4])
    
    mock_df = generate_mock_prices(trigger_level, target_1, target_2)
    run_buy_engine(w_df, mock_df, frozen_price=price)