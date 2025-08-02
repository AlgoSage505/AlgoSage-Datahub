import math

def mround(x, base=0.25):
    return round(base * round(float(x) / base), 2) if base else round(x, 2)

def calculate_short_levels(price):
    if price <= 0:
        raise ValueError("Price must be positive")
    
    m93 = (math.sqrt(price) - 2) ** 2
    n65 = (price - m93) / 24  # Positive decrement step
    n66 = price - m93
    
    print("Short Side Calculation")
    print("----------------------")
    print("Price entered:       ", price)
    print("Max Downside (M93):  ", mround(m93))
    print("360° Level diff:     ", mround(n66))
    print("15° Level decrement: ", mround(n65))
    
    levels = []
    level = price
    for deg in range(15, 375, 15):
        level -= n65
        rounded_level = mround(level)
        percent = (price - rounded_level) / n66 * 100 if n66 else 0
        levels.append({'degree': deg, 'level': rounded_level, 'percent': round(percent, 2)})
    
    print("\nCalculated Short Levels:")
    for item in levels:
        print(f"{item['degree']}° ➔ {item['level']} ({item['percent']}%)")
    
    return levels

# Example usage
if __name__ == "__main__":
    price = float(input("Enter price for short levels: ") or 2380)
    calculate_short_levels(price)