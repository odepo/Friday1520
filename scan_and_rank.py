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
        
        df = yf.download(ticker, period="2y", interval="1wk", progress=False)
        if df.empty or len(df) < 30: return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close_col = 'Close'
        df['rci9'] = calculate_rci(df[close_col], 9)
        
        # VCP分析用：ボラティリティ
        df['high_low_range'] = (df['High'] - df['Low']) / df['Low'] * 100
        w3_volatility = df['high_low_range'].iloc[-5:].mean() 
        
        # 需給分析用：出来高
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

        # --- 軍師による多角的な分析コメント生成 ---
        rank = "C"; stats = None
        advice = "【偵察】\nまだ敵（売り圧力）が多い。静観し、戦機（需給の引き締まり）を待て。"
        
        if rci_rev:
            if vcp_score >= 80:
                rank = "A"; stats = STATS_RANK_A
                advice = (f"【総攻撃の好機：RANK A】\n"
                          f"①反撃の狼煙：週足RCIが底部({rci_val})から反転。底打ちを確認。\n"
                          f"②兵糧攻め：出来高が平均の{v_ratio}%まで激減。売り手が不在だ。\n"
                          f"③陣形：ボラが{w3_volatility:.1f}%まで収縮。爆発準備完了。\n"
                          f"★チャートで『直近の小高い山』を抜けるか注視せよ！")
            else:
                rank = "B"
                advice = (f"【戦備を整えよ：RANK B】\n"
                          f"RCIは好転したが、まだ値動きに迷いがある。ボラ({w3_volatility:.1f}%)が5%を切るのを待て。\n"
                          f"★チャートで移動平均線が『横ばい』になっているか確認。")
        elif vcp_score >= 50:
            rank = "B"
            advice = (f"【嵐の前の静けさ：RANK B】\n"
                      f"ボラは絞られてきたがRCIがまだ下向きだ。反転の兆しを待て。")

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
            "comment": advice
        }
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

if __name__ == "__main__":
    results = []
    for t in WATCH_LIST:
        res = analyze_stock(t)
        if res: results.append(res)
            
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
