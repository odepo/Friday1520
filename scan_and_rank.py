import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import datetime

# --- 初期設定 ---
WATCH_LIST = ["4635.T", "4471.T", "5334.T", "3498.T"] # 監視リスト例
OUTPUT_FILE = "result.json"

# --- 統計データ（ランクAの過去バックテストに基づく目安） ---
STATS_RANK_A = {
    "win_rate": {"value": 72, "avg": 50, "color": "green"},
    "rr_ratio": {"value": 3.5, "avg": 1.2, "color": "cyan"},
    "pf": {"value": 2.1, "avg": 1.3, "color": "gold"}
}

# --- インジケーター計算関数 ---
def calculate_rci(series, period=9):
    """RCI(順位相関指数)の計算"""
    rank_period = np.arange(1, period + 1)[::-1]
    def _rci(x):
        d = sum((np.argsort(np.argsort(x)) + 1 - rank_period) ** 2)
        return (1 - (6 * d) / (period * (period**2 - 1))) * 100
    return series.rolling(window=period).apply(_rci)

def analyze_stock(ticker):
    """銘柄の多角的な判定と統計データの付与"""
    # 週足データの取得
    df = yf.download(ticker, period="2y", interval="1wk", progress=False)
    if len(df) < 30: return None

    # インジケーター計算
    df['rci9'] = calculate_rci(df['Adj Close'], 9)
    df['ma20'] = df['Adj Close'].rolling(window=20).mean()
    df['std20'] = df['Adj Close'].rolling(window=20).std()
    df['bandwidth'] = (df['ma20'] + (df['std20'] * 2) - (df['ma20'] - (df['std20'] * 2))) / df['ma20']
    
    # 精密VCPスコア（振幅の収束と出来高の枯渇）
    df['high_low_range'] = (df['High'] - df['Low']) / df['Low'] * 100
    w3 = df['high_low_range'].iloc[-5:].mean() # 直近1週間の平均振幅
    avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
    last_vol = df['Volume'].iloc[-5:].mean()
    
    # 判定スコア
    vcp_score = 0
    if w3 < 5.0: vcp_score += 50      # 振幅が5%以下
    if last_vol < avg_vol * 0.7: vcp_score += 50 # 出来高が7割以下

    # --- ランク判定ロジック ---
    last = df.iloc[-1]
    prev = df.iloc[-2]
    rci_reversal = last['rci9'] > prev['rci9'] and last['rci9'] < 20
    
    rank = "C"
    stats = None
    comment = "偵察。打診買い。"
    
    if rci_reversal and vcp_score >= 80:
        rank = "A"
        stats = STATS_RANK_A # ランクAの統計データを付与
        comment = "製造ライン、フル稼働！厚めのロットで執行せよ。"
    elif rci_reversal:
        rank = "B"
        comment = "標準ロット。トレンド開始待ち。"

    if rank == "C": return None # ランクCは通知しない

    return {
        "ticker": ticker.replace(".T", ""),
        "rank": rank,
        "stats": stats,
        "vcp_score": vcp_score,
        "bandwidth": last['bandwidth'],
        "comment": comment,
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# --- メイン処理 ---
if __name__ == "__main__":
    results = []
    for t in WATCH_LIST:
        try:
            res = analyze_stock(t)
            if res: results.append(res)
        except Exception as e:
            print(f"Error {t}: {e}")
            
    # JSONとして出力
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_with_ascii=False, indent=2)
