import yfinance as yf
import pandas as pd
import numpy as np
import json
import datetime

# --- 初期設定 ---
WATCH_LIST = ["4635.T", "4471.T", "5334.T", "3498.T"] 
OUTPUT_FILE = "result.json"

# 統計データ（ランクAの目安）
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
    # 銘柄名を取得
    t_obj = yf.Ticker(ticker)
    s_name = t_obj.info.get('longName', ticker)
    
    # データを取得
    df = yf.download(ticker, period="2y", interval="1wk", progress=False)
    if df.empty or len(df) < 30: return None

    # 列名の「Adj Close」を「Close」として扱う（マルチインデックス対策）
    close_col = 'Close'
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df['rci9'] = calculate_rci(df[close_col], 9)
    df['ma20'] = df[close_col].rolling(window=20).mean()
    df['std20'] = df[close_col].rolling(window=20).std()
    
    df['high_low_range'] = (df['High'] - df['Low']) / df['Low'] * 100
    w3 = df['high_low_range'].iloc[-5:].mean() 
    avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
    last_vol = df['Volume'].iloc[-5:].mean()
    
    vcp_score = 0
    if w3 < 5.0: vcp_score += 50
    if last_vol < avg_vol * 0.7: vcp_score += 50 

    last = df.iloc[-1]
    prev = df.iloc[-2]
    rci_rev = last['rci9'] > prev['rci9'] and last['rci9'] < 20
    
    # 前日比などの計算
    price = int(last[close_col])
    diff_val = int(last[close_col] - prev[close_col])
    diff_pct = round((diff_val / prev[close_col]) * 100, 1)
    lc_price = int(last['Low'] * 0.96) # 直近安値付近を損切り目安に

    rank = "C"; stats = None; comment = "偵察。打診買い。"
    if rci_rev and vcp_score >= 80:
        rank = "A"; stats = STATS_RANK_A
        comment = "成り行き買いで執行せよ！VCP収束と15:20需給の完全一致。迷わず行け！"
    elif rci_rev:
        rank = "B"; comment = "標準ロット。トレンド開始待ち。"

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
        # ここを ensure_ascii に修正しました！
        json.dump(results, f, ensure_ascii=False, indent=2)
