import pandas as pd
import os

d = 'E:/量化研究/workspace/stock/output'
for f in sorted(os.listdir(d)):
    if 'consecutive_bullish' in f and '0801' in f:
        if f.endswith('.xlsx'):
            df = pd.read_excel(os.path.join(d, f))
            print(f'【连续小阳线】({len(df)}只)')
            print(df.to_string(index=False))
            
    if f.endswith('.csv') and '0801' in f:
        df = pd.read_csv(os.path.join(d, f))
        nm = f.split('_2026')[0]
        cols = [c for c in ['代码','code','名称','name','close','price','change_percent','change'] if c in df.columns]
        if cols:
            print(f'\n【{nm}】({len(df)}只)')
            print(df[cols].head(15).to_string(index=False))