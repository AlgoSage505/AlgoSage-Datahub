import math

def mround(x, base=0.25):
    return round(base * round(float(x) / base), 2) if base else round(x, 2)

def theory2_short(price):  # Narrower (AP-based, short-term theory)
    sqrt_price = math.sqrt(price)
    ap19 = int(sqrt_price)
    ap11 = ap19 + 1
    step = (ap11 - ap19) / 8
    ap_values = [ap11 - i * step for i in range(9)]
    levels = [mround(x ** 2) for x in ap_values]
    return levels, ap_values  # Return levels and roots for debug

def theory2_long(price):  # Wider (AO-based, long-term theory)
    sqrt_price = math.sqrt(price)
    ap19 = int(sqrt_price)
    ap11 = ap19 + 1
    ao11 = ap11 + 1
    ao19 = ap19 - 1
    step = (ao11 - ao19) / 8
    ao_values = [ao11 - i * step for i in range(9)]
    levels = [mround(x ** 2) for x in ao_values]
    return levels, ao_values

# Example usage and print
if __name__ == "__main__":
    price = float(input("Enter price for Theory 2: ") or 2380)
    short_levels, ap_roots = theory2_short(price)
    long_levels, ao_roots = theory2_long(price)
    
    print("Short-Term Theory (AP Roots and Levels):")
    for i in range(9):
        print(f"AP{11+i}: Root={ap_roots[i]:.2f}  Level={short_levels[i]}")
    
    print("\nLong-Term Theory (AO Roots and Levels):")
    for i in range(9):
        print(f"AO{11+i}: Root={ao_roots[i]:.2f}  Level={long_levels[i]}")