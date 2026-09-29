import os, time, requests, datetime
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT=os.getenv("TELEGRAM_CHAT_ID")

STOCKS=["SJVN","HUDCO","RVNL","IRFC","BDL","MAZDOCK","BEL","NHPC","SUZLON","BSE","CDSL","KFINTECH","KAYNES","DIXON","PGEL","POLYCAB","NCC","NBCC","IRB","LTF","MUTHOOTFIN","FEDERALBNK","LAURUSLABS","LTIM","PERSISTENT","COFORGE","IEX","IFCI","RPOWER","JWL","TITAGARH","ELECON","RAYMOND","RBLBANK","BSOFT","CYIENT","MAPMYINDIA","JINDALSAW","GODREJIND","VGUARD","CROMPTON","VOLTAS","BLUESTAR"]

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id":CHAT,"text":m}, timeout=10)
        time.sleep(3)
    except: time.sleep(3)

def check_one(sym):
    try:
        df=yf.Ticker(sym+".NS").history(period="5d", interval="5m")
        if len(df)<40: return None
        df['E9']=df['Close'].ewm(span=9).mean(); df['E15']=df['Close'].ewm(span=15).mean()
        df['VWAP']=(df['Close']*df['Volume']).cumsum()/df['Volume'].cumsum(); df['VA']=df['Volume'].rolling(20).mean()
        l=df.iloc[-1]; p=df.iloc[-2]
        ltp=float(l['Close']); e9=float(l['E9']); e15=float(l['E15']); e9p=float(p['E9']); e15p=float(p['E15']); vwap=float(l['VWAP']); vwapp=float(p['VWAP']); vol=float(l['Volume']); avg=float(l['VA']); volx=vol/avg if avg>0 else 1
        day_low=float(df['Low'].tail(78).min()); day_high=float(df['High'].tail(78).max())
        
        if ltp<35 or ltp>2500: return None
        score=10 + (3 if ltp>vwap else 0) + (3 if e9>e15 else 0) + (4 if volx>1.5 else 0)
        if score<15.5 or volx<1.5: return None

        # === BUY - BOTTOM BREAKOUT ===
        if ltp>vwap>e9>e15 and e9p<e15p and e9>e15 and vwapp<e9p and vwap>e9 and l['Close']>l['Open']:
            near_low = (ltp-day_low)/day_low*100
            near_high = (day_high-ltp)/day_high*100
            if 0.3 <= near_low <= 5.0 or near_high <= 1.5: # तुझं 5,6 Bottom
                # === SL + TRAILING LOGIC ===
                init_sl = min(ltp*0.99, e9*0.998, day_low*0.995) # Initial SL 1% किंवा 9EMA किंवा Day Low
                t1 = ltp*1.012
                t2 = ltp*1.025
                trail_sl = max(e9*0.998, ltp*0.992) # Trailing SL - 9EMA किंवा LTP च्या 0.8% खाली
                return {"s":sym,"ltp":ltp,"t":"BUY","sc":score,"vx":round(volx,1),"sl":round(init_sl,2),"tsl":round(trail_sl,2),"t1":round(t1,2),"t2":round(t2,2),"e9":round(e9,2)}

        # === SELL - TOP BREAKDOWN ===
        if ltp<vwap<e9<e15 and e9p>e15p and e9<e15 and vwapp>e9p and vwap<e9 and l['Close']<l['Open']:
            near_high = (day_high-ltp)/day_high*100
            if 0.3 <= near_high <= 5.0:
                init_sl = max(ltp*1.01, e9*1.002, day_high*1.005)
                t1 = ltp*0.988
                t2 = ltp*0.975
                trail_sl = min(e9*1.002, ltp*1.008)
                return {"s":sym,"ltp":ltp,"t":"SELL","sc":score,"vx":round(volx,1),"sl":round(init_sl,2),"tsl":round(trail_sl,2),"t1":round(t1,2),"t2":round(t2,2),"e9":round(e9,2)}
    except: return None

def main():
    now=datetime.datetime.now()
    found=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs={ex.submit(check_one,s):s for s in STOCKS}
        for f in as_completed(futs):
            r=f.result()
            if r: found.append(r)
    found=sorted(found, key=lambda x:x['sc'], reverse=True)[:6] # तुझं 5,6 Signal

    if not found:
        tg(f"⚡ V43 BUY/SELL+TSL {now.strftime('%H:%M')} | Scanned {len(STOCKS)} | Found 0 Real | Bot Alive ✅")
        return

    tg(f"🚀 V43 {len(found)} BREAKOUT + TRAILING SL {now.strftime('%H:%M')}")
    for st in found:
        if st['t']=='BUY':
            tg(f"🟢 BUY {st['s']} @{st['ltp']}\nSL: {st['sl']} (Init) | TSL: {st['tsl']} (Trail 9EMA)\nT1: {st['t1']} | T2: {st['t2']}\nVol {st['vx']}x | S:{st['sc']} | 9EMA {st['e9']}\nRule: LTP> {st['tsl']} राहिला तर Hold, खाली आला तर Exit")
        else:
            tg(f"🔴 SELL {st['s']} @{st['ltp']}\nSL: {st['sl']} (Init) | TSL: {st['tsl']} (Trail 9EMA)\nT1: {st['t1']} | T2: {st['t2']}\nVol {st['vx']}x | S:{st['sc']} | 9EMA {st['e9']}\nRule: LTP< {st['tsl']} राहिला तर Hold, वर गेला तर Exit")

if __name__=="__main__": main()
