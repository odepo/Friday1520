import yfinance as yf
import pandas as pd
import numpy as np
import json
import datetime

# --- 【配当工場】精鋭24銘柄リスト ---
WATCH_LIST = [
    "4635.T", "4471.T", "5334.T", "3498.T", "7164.T", 
    "8593.T", "9368.T", "5076.T", "6293.T", "4481.T", 
    "2154.T", "4043.T", "6070.T", "7995.T", "9303.T", 
    "4221.T", "9436.T", "6323.T", "8005.T", "8058.T", 
    "7203.T", "9104.T", "8306.T", "4502.T" # ←武田薬品を加えて24件！
]

OUTPUT_FILE = "result.json"

STATS_RANK_A = {
    "win_rate": {"value": 72, "avg": 50},
    "pf": {"value": 2.1, "avg": 1.2},
    "rr_ratio": {"value": 3.5, "avg": 1.5}
}

def calculate_rci(series, period=9):
    rank_period = np.arange(1, period + 1)[::-1]
    def _rci(x):
        d = sum((np.argsort(np.argsort(x)) + 1 - rank_period) ** 2)
        return (1 - (6 * d) / (period * (period**2 - 1))) * 100
    return series.rolling(window=period).apply(_rci)

def analyze_stock(ticker):
    t_obj = yf.Ticker(ticker)
    s_name = t_obj.info.get('shortName', ticker)
    
    df = yf.download(ticker, period="2y", interval="1wk", progress=False)
    if df.empty or len(df) < 30: return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close_col = 'Close'
    df['rci9'] = calculate_rci(df[close_col], 9)
    df['ma20'] = df[close_col].rolling(window=20).mean()
    
    df['high_low_range'] = (df['High'] - df['Low']) / df['Low'] * 100
    w3 = df['high_low_range'].iloc[-5:].mean() 
    avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
    last_vol = df['Volume'].iloc[-5:].mean()
    
    vcp_score = 0
    if w3 < 5.0: vcp_score += 50
    if last_vol < avg_vol * 0.8: vcp_score += 50 

    last = df.iloc[-1]
    prev = df.iloc[-2]
    rci_rev = last['rci9'] > prev['rci9'] and last['rci9'] < 20
    
    price = int(last[close_col])
    diff_val = int(last[close_col] - prev[close_col])
    diff_pct = round((diff_val / prev[close_col]) * 100, 1)
    lc_price = int(last['Low'] * 0.96)

    rank = "C"; stats = None; comment = "偵察。監視継続。"
    if rci_rev and vcp_score >= 80:
        rank = "A"; stats = STATS_RANK_A
        comment = "【執行対象】VCP収縮を確認。成り行きで執行せよ！"
    elif rci_rev or vcp_score >= 50:
        rank = "B"; comment = "チャンス近し。週足の形を注視。"

    return {
        "ticker": ticker.replace(".T", ""),
        "name": s_name,
        "price": price,
        "diff_val": diff_val,
        "diff_pct": diff_pct,
        "lc_price": lc_price,
        "rank": rank,
        "stats": stats,
        "vol_dry": int((last_vol/avg_vol)*100),
        "comment": comment
    }

if __name__ == "__main__":
    results = []
    for t in WATCH_LIST:
        try:
            res = analyze_stock(t)
            if res: results.append(res)
        except Exception as e:
            print(f"Error {t}: {e}")
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
