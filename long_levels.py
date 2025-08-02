import math

def mround(x, base=0.25):
    return round(base * round(float(x) / base), 2) if base else round(x, 2)

def calculate_long_levels(price):
    if price <= 0:
        raise ValueError("Price must be positive")
    
    g93 = (math.sqrt(price) + 2) ** 2
    h65 = (g93 - price) / 24
    h66 = g93 - price
    
    print("Long Side Calculation")
    print("---------------------")
    print("Price entered:       ", price)
    print("Max Upside (G93):    ", mround(g93))
    print("360° Level diff:     ", mround(h66))
    print("15° Level increment: ", mround(h65))
    
    levels = []
    level = price
    for deg in range(15, 375, 15):
        level += h65
        rounded_level = mround(level)
        percent = (rounded_level - price) / h66 * 100 if h66 else 0
        levels.append({'degree': deg, 'level': rounded_level, 'percent': round(percent, 2)})
    
    print("\nCalculated Long Levels:")
    for item in levels:
        print(f"{item['degree']}° ➔ {item['level']} ({item['percent']}%)")
    
    return levels

# Example usage
if __name__ == "__main__":
    price = float(input("Enter price for long levels: ") or 2380)
    calculate_long_levels(price)