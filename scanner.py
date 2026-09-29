import os, time, requests, datetime
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

# SMALL + MID ONLY - 45 STOCK - LARGE BLOCK
STOCKS = ["SJVN","HUDCO","RVNL","IRFC","BDL","MAZDOCK","BEL","NHPC","SUZLON","BSE","CDSL","KFINTECH","KAYNES","DIXON","PGEL","POLYCAB","NCC","NBCC","IRB","LTF","MUTHOOTFIN","FEDERALBNK","LAURUSLABS","LTIM","PERSISTENT","COFORGE","IEX","IFCI","RPOWER","JWL","TITAGARH","ELECON","RAYMOND","RBLBANK","BSOFT","CYIENT","MAPMYINDIA","JINDALSAW","GODREJIND","VGUARD","CROMPTON","VOLTAS","BLUESTAR","IDEA"]

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id": CHAT, "text": m}, timeout=15)
        time.sleep(3) # Flood Fix
    except: time.sleep(3)

def check(sym):
    try:
        df = yf.Ticker(sym + ".NS").history(period="5d", interval="5m")
        if len(df) < 40: return None
        
        df['E9'] = df['Close'].ewm(span=9).mean()
        df['E15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = (df['Close']*df['Volume']).cumsum()/df['Volume'].cumsum()
        df['VA'] = df['Volume'].rolling(20).mean()
        
        l = df.iloc[-1]; p = df.iloc[-2]
        ltp = float(l['Close']); e9 = float(l['E9']); e15 = float(l['E15'])
        e9p = float(p['E9']); e15p = float(p['E15'])
        vwap = float(l['VWAP']); vwapp = float(p['VWAP'])
        vol = float(l['Volume']); avg = float(l['VA'])
        volx = vol/avg if avg>0 else 0
        
        day_low = float(df['Low'].tail(78).min())
        day_high = float(df['High'].tail(78).max())

        if ltp < 35 or ltp > 3000: return None
        if volx < 1.5: return None # Vol Must 1.5x

        score = 10
        if ltp > vwap: score+=3
        if e9 > e15: score+=3
        if volx > 1.5: score+=4
        if score < 15.5: return None # V25 चा S:7.9 Block

        # === 1. BOTTOM BREAKOUT - BUY ===
        if ltp > vwap > e9 > e15 and e9p < e15p and e9 > e15 and vwapp < e9p and vwap > e9 and l['Close'] > l['Open']:
            near_low = (ltp - day_low)/day_low*100
            near_high = (day_high - ltp)/day_high*100
            if (0.3 <= near_low <= 6.0) or (near_high <= 1.5): # तुझं 5,6 Bottom
                sl = min(ltp*0.99, e9*0.998, day_low*0.995)
                tsl = max(e9*0.998, ltp*0.992) # Trailing SL
                t1 = ltp*1.012; t2 = ltp*1.028
                return {"s": sym, "ltp": ltp, "t": "BUY", "sc": score, "vx": round(volx,1), "sl": round(sl,2), "tsl": round(tsl,2), "t1": round(t1,2), "t2": round(t2,2)}

        # === 2. TOP BREAKDOWN - SELL ===
        if ltp < vwap < e9 < e15 and e9p > e15p and e9 < e15 and vwapp > e9p and vwap < e9 and l['Close'] < l['Open']:
            near_high = (day_high - ltp)/day_high*100
            if 0.3 <= near_high <= 6.0: # Top 5,6%
                sl = max(ltp*1.01, e9*1.002, day_high*1.005)
                tsl = min(e9*1.002, ltp*1.008)
                t1 = ltp*0.988; t2 = ltp*0.972
                return {"s": sym, "ltp": ltp, "t": "SELL", "sc": score, "vx": round(volx,1), "sl": round(sl,2), "tsl": round(tsl,2), "t1": round(t1,2), "t2": round(t2,2)}

    except: return None

def main():
    now = datetime.datetime.now()
    found = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {ex.submit(check, s): s for s in STOCKS}
        for f in as_completed(futs):
            r = f.result()
            if r: found.append(r)
    
    found = sorted(found, key=lambda x: x['sc'], reverse=True)[:6] # तुझं 5,6 Signal

    if not found:
        tg(f"⚡ V44 BUY+SELL+TSL {now.strftime('%H:%M')} | Scan {len(STOCKS)} | Found 0 Real | 0 Fake ✅\nLogic: 9x15 Fresh+VWAPx9+Vol1.5x+S15.5+5m Candle | Bot Alive")
        return

    tg(f"🚀 V44 {len(found)} REAL SIGNAL {now.strftime('%H:%M')}")
    for x in found:
        if x['t'] == 'BUY':
            tg(f"🟢 BUY {x['s']} @{x['ltp']}\nSL {x['sl']} | TSL {x['tsl']} (9EMA Trail)\nT1 {x['t1']} | T2 {x['t2']} | Vol {x['vx']}x S:{x['sc']}\nHold Till LTP>TSL")
        else:
            tg(f"🔴 SELL {x['s']} @{x['ltp']}\nSL {x['sl']} | TSL {x['tsl']} (9EMA Trail)\nT1 {x['t1']} | T2 {x['t2']} | Vol {x['vx']}x S:{x['sc']}\nHold Till LTP<TSL")

if __name__ == "__main__":
    main()
