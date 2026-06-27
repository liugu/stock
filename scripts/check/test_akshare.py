import akshare as ak
print("Testing akshare...")
try:
    df = ak.stock_zh_a_spot_em()
    print(f"Got {len(df)} stocks")
    print(df.head(3))
except Exception as e:
    print(f"Error: {e}")