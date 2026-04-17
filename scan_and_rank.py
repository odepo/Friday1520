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
    "7203.T", "9104.T", "8306.T", "4502.T"
]

OUTPUT_FILE = "result.json"

# RANK Aの期待値データ
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
    try:
        t_obj = yf.Ticker(ticker)
        s_name = t_obj.info.get('shortName', ticker)
        
        # 週足データの取得
        df = yf.download(ticker, period="2y", interval="1wk", progress=False)
        if df.empty or len(df) < 30: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 指標計算
        close_col = 'Close'
        df['rci9'] = calculate_rci(df[close_col], 9)
        df['high_low_range'] = (df['High'] - df['Low']) / df['Low'] * 100
        w3_volatility = df['high_low_range'].iloc[-5:].mean() 
        avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
        last_vol = df['Volume'].iloc[-5:].mean()
        v_ratio = int(last_vol / avg_vol * 100)
        
        # スコアリング
        vcp_score = 0
        if w3_volatility < 5.0: vcp_score += 50
        if last_vol < avg_vol * 0.8: vcp_score += 50 

        last = df.iloc[-1]
        prev = df.iloc[-2]
        rci_val = int(last['rci9'])
        rci_rev = last['rci9'] > prev['rci9'] and last['rci9'] < 20
        
        price = int(last[close_col])
        diff_val = int(last[close_col] - prev[close_col])
        diff_pct = round((diff_val / prev[close_col]) * 100, 1)
        lc_price = int(last['Low'] * 0.96)

        # --- 活用ガイド型・軍師コメント生成 ---
        rank = "C"; stats = None
        advice = "【偵察】まだ戦機にあらず。静観せよ。"
        
        if rci_rev or vcp_score >= 50:
            if rci_rev and vcp_score >= 80:
                rank = "A"; stats = STATS_RANK_A
                title = "🚀【総攻撃】執行せよ！"
            else:
                rank = "B"; title = "🏹【準備】監視を強めよ"
            
            advice = (f"{title}\n"
                      f"------------------------\n"
                      f"📉 チャート調査の3か条ガイド\n"
                      f"1. RCI反転(狼煙): 現在 {rci_val}\n"
                      f"   目視：谷底から這い上がったか？\n"
                      f"2. VCP収縮(陣形): 現在 {w3_volatility:.1f}%\n"
                      f"   目視：細い糸のように並んでいるか？\n"
                      f"3. 売り枯れ(兵糧): 現在 {v_ratio}%\n"
                      f"   目視：出来高が地面に這っているか？\n"
                      f"------------------------\n"
                      f"★上記3点が『合致』なら成り行き執行！")

        return {
            "ticker": ticker.replace(".T", ""), "name": s_name, "price": price,
            "diff_val": diff_val, "diff_pct": diff_pct, "lc_price": lc_price,
            "rank": rank, "stats": stats, "vol_dry": v_ratio, "comment": advice
        }
    except Exception: return None

if __name__ == "__main__":
    results = []
    for t in WATCH_LIST:
        res = analyze_stock(t)
        if res: results.append(res)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
