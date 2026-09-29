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
        if ltp<35 or ltp>2500: return None
        score=10 + (3 if ltp>vwap else 0) + (3 if e9>e15 else 0) + (4 if volx>1.5 else 0)
        if score<15.5 or volx<1.5: return None # हा Line V25 मध्ये नव्हता - म्हणून 500 Fake आले!
        if ltp>vwap>e9>e15 and e9p<e15p and e9>e15 and vwapp<e9p and vwap>e9 and l['Close']>l['Open']:
            return {"s":sym,"ltp":ltp,"t":"BUY","sc":score,"vx":round(volx,1)}
        if ltp<vwap<e9<e15 and e9p>e15p and e9<e15 and vwapp>e9p and vwap<e9 and l['Close']<l['Open']:
            return {"s":sym,"ltp":ltp,"t":"SELL","sc":score,"vx":round(volx,1)}
    except: return None

def main():
    now=datetime.datetime.now()
    found=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs={ex.submit(check_one,s):s for s in STOCKS}
        for f in as_completed(futs):
            r=f.result()
            if r: found.append(r)
    found=sorted(found, key=lambda x:x['sc'], reverse=True)[:10] # TOP 10 ONLY - V25 मध्ये 500 होता!
    if not found:
        tg(f"⚡ V42 FAST {now.strftime('%H:%M')} | Scanned {len(STOCKS)} | Found 0 Real | 0 Fake Blocked ✅\nCond: 9EMA x 15EMA Fresh + VWAP x 9EMA + Vol 1.5x + Score 15.5+ | Small+Mid Only | Bot Alive")
        return
    tg(f"🚀 V42 FAST {len(found)} REAL BREAKOUT {now.strftime('%H:%M')} | {len(STOCKS)} STOCKS")
    for st in found:
        tg(f"{'🟢 BUY' if st['t']=='BUY' else '🔴 SELL'} {st['s']} @{st['ltp']:.2f} SL {st['ltp']*0.99:.2f} | Vol {st['vx']}x | S:{st['sc']} | 5m Bottom/Top")

if __name__=="__main__": main()
