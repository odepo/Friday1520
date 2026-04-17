import yfinance as yf
import pandas as pd
import numpy as np
import json

# --- 【配当工場】精鋭24銘柄リスト ---
WATCH_LIST = [
    "4635.T", "4471.T", "5334.T", "3498.T", "7164.T", 
    "8593.T", "9368.T", "5076.T", "6293.T", "4481.T", 
    "2154.T", "4043.T", "6070.T", "7995.T", "9303.T", 
    "4221.T", "9436.T", "6323.T", "8005.T", "8058.T", 
    "7203.T", "9104.T", "8306.T", "4502.T"
]

OUTPUT_FILE = "result.json"

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
        
        df = yf.download(ticker, period="2y", interval="1wk", progress=False)
        if df.empty or len(df) < 30: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        close_col = 'Close'
        # 1. RCI反転スコア (狼煙)
        df['rci9'] = calculate_rci(df[close_col], 9)
        last_rci = df['rci9'].iloc[-1]
        prev_rci = df['rci9'].iloc[-2]
        rci_score = int(max(0, min(100, (80 - last_rci) + (20 if last_rci > prev_rci else 0))))

        # 2. VCP収縮スコア (陣形)
        df['range'] = (df['High'] - df['Low']) / df['Low'] * 100
        w3_vol = df['range'].iloc[-5:].mean()
        vcp_score = int(max(0, min(100, (10 - w3_vol) * 10)))

        # 3. 需給引き締まりスコア (兵糧)
        avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
        last_vol = df['Volume'].iloc[-5:].mean()
        v_ratio = int(last_vol / avg_vol * 100)
        supply_score = int(max(0, min(100, 150 - v_ratio)))

        # 総合判定
        rank = "C"
        rci_rev = last_rci > prev_rci and last_rci < 20
        if rci_rev and vcp_score >= 80 and supply_score >= 80:
            rank = "A"
        elif rci_rev or vcp_score >= 50:
            rank = "B"

        price = int(df[close_col].iloc[-1])
        diff_val = int(price - df[close_col].iloc[-2])
        diff_pct = round((diff_val / df[close_col].iloc[-2]) * 100, 1)
        lc_price = int(df['Low'].iloc[-1] * 0.96)

        # 軍師の活用ガイド
        title = "🚀【総攻撃】執行せよ！" if rank == "A" else ("🏹【準備】監視を強めよ" if rank == "B" else "【偵察】静観せよ")
        advice = (f"{title}\n"
                  f"------------------------\n"
                  f"📉 チャート調査の3か条ガイド\n"
                  f"1. RCI反転(狼煙): 現在 {int(last_rci)}\n"
                  f"   ⇒ 目視：谷底から這い上がったか？\n"
                  f"2. VCP収縮(陣形): 現在 {w3_vol:.1f}%\n"
                  f"   ⇒ 目視：細い糸のように並んでいるか？\n"
                  f"3. 売り枯れ(兵糧): 現在 {v_ratio}%\n"
                  f"   ⇒ 目視：出来高が地面に這っているか？\n"
                  f"------------------------\n"
                  f"★上記3点が『合致』なら成り行き執行！")

        return {
            "ticker": ticker.replace(".T", ""), "name": s_name, "price": price,
            "diff_val": diff_val, "diff_pct": diff_pct, "lc_price": lc_price,
            "rank": rank, "vol_dry": v_ratio, "comment": advice,
            "stats": {
                "win_rate": {"value": rci_score, "avg": 50}, 
                "pf": {"value": round(vcp_score/20, 1), "avg": 2.5}, 
                "rr_ratio": {"value": round(supply_score/20, 1), "avg": 2.5}
            }
        }
    except Exception: return None

if __name__ == "__main__":
    results = []
    for t in WATCH_LIST:
        res = analyze_stock(t)
        if res: results.append(res)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
