# scanner.py - V41 FINAL - SMALL+MID ONLY - 120 Stocks
# 9EMA x 15EMA Fresh Cross + VWAP x 9EMA Cross + 5M High Vol Bottom/Top + Score 15.5+
# LargeCap 100% Block - Message 100% Yega

import os, time, requests, datetime
import yfinance as yf
import pandas as pd

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

# ===== PURE SMALL + MID 120 - NO LARGE =====
STOCKS = [
# MIDCAP 60
"SJVN","HUDCO","RVNL","IRFC","BDL","MAZDOCK","COCHINSHIP","GRSE","BEML","BEL",
"NHPC","SUZLON","INOXWIND","SWSOLAR","KPIGREEN","INOXGREEN","BSE","CDSL",
"KFINTECH","CAMS","ANANDRATHI","NUVAMA","MOTILALOFS","KAYNES","SYRMA","DIXON",
"PGEL","AMBER","ASTRAL","POLYCAB","KEI","NCC","NBCC","IRB","LTF","MUTHOOTFIN",
"MANAPPURAM","PNBHOUSING","FEDERALBNK","KARURVYSYA","IDFCFIRSTB","LAURUSLABS",
"GRANULES","IPCALAB","AJANTPHARM","NATCOPHARM","LTIM","PERSISTENT","COFORGE",
"LTTS","TATAELXSI","KPIT","360ONE","IEX","MCX","DELHIVERY","BLS","PRAJIND",

# SMALLCAP 60 - REAL BREAKOUT
"IFCI","RPOWER","JWL","TEXRAIL","JUPITERWAG","TITAGARH","TRITURBINE","ELECON",
"JYOTISTRUC","INOXINDIA","BOMDYEING","RAYMOND","RBLBANK","UJJIVANSFB","EQUITASBNK",
"VGUARD","CROMPTON","VOLTAS","BLUESTAR","WHIRLPOOL","BSOFT","FSL","CYIENT",
"ZENSAR","TATATECH","INTELLECT","MAPMYINDIA","AFFLE","LATENTVIEW","FIVESTAR",
"JINDALSAW","WELSPUNLIV","RATNAMANI","FINCABLES","CHOLAHLDNG","KNRCON","KPIL",
"GODREJIND","WELCORP","ELECON","PNCINFRA","HGINFRA","ANANTRAJ","SOBHA","BRIGADE",
"OBEROIRLTY","PRESTIGE","LODHA","GODREJPROP","DLF","PHOENIXLTD"
]

# LARGE DELETE - Screenshot wale saare fake
LARGE = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","BAJFINANCE","MARUTI","KOTAKBANK","AXISBANK","WIPRO","HCLTECH","ASIANPAINT","ULTRACEMCO","ADANIENT","ADANIPOWER","JSWSTEEL","TATASTEEL","BPCL","JIOFIN","BANKBARODA","CANBK","HDFCLIFE","ICICIPRULI","MAXHEALTH","GODREJCP","DABUR","PETRONET","MOTHERSON","TITAN","DAMCAPITAL","RCF","MAHABANK","POWERGRID","NTPC","ONGC","JSWENERGY","TATAPOWER","HINDUNILVR","NESTLEIND","SBILIFE","BAJAJFINSV"]

def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id": CHAT, "text": msg}, timeout=10)
        time.sleep(3)
    except: time.sleep(5)

def check(sym):
    if sym in LARGE: return None
    try:
        df = yf.Ticker(sym+".NS").history(period="5d", interval="5m")
        if len(df)<40: return None
        df['E9']=df['Close'].ewm(span=9).mean()
        df['E15']=df['Close'].ewm(span=15).mean()
        df['VWAP']=(df['Close']*df['Volume']).cumsum()/df['Volume'].cumsum()
        df['VA']=df['Volume'].rolling(20).mean()
        l=df.iloc[-1]; p=df.iloc[-2]
        ltp=float(l['Close']); e9=float(l['E9']); e15=float(l['E15']); e9p=float(p['E9']); e15p=float(p['E15']); vwap=float(l['VWAP']); vwapp=float(p['VWAP']); vol=float(l['Volume']); avg=float(l['VA']); volx=vol/avg if avg>0 else 1
        score=10
        if ltp>vwap: score+=3
        if e9>e15: score+=3
        if volx>1.5: score+=4
        if ltp<40 or ltp>2500: return None
        if score<15.5: return None
        if volx<1.5: return None
        # BUY - Bottom
        if ltp>vwap>e9>e15:
            if e9p<e15p and e9>e15 and vwapp<e9p and vwap>e9:
                if l['Close']>l['Open']:
                    return {"s":sym,"ltp":ltp,"t":"BUY","sc":score,"vx":round(volx,1),"e9":round(e9,1),"e15":round(e15,1),"vw":round(vwap,1)}
        # SELL - Top
        if ltp<vwap<e9<e15:
            if e9p>e15p and e9<e15 and vwapp>e9p and vwap<e9:
                if l['Close']<l['Open']:
                    return {"s":sym,"ltp":ltp,"t":"SELL","sc":score,"vx":round(volx,1),"e9":round(e9,1),"e15":round(e15,1),"vw":round(vwap,1)}
    except: return None

def main():
    now=datetime.datetime.now()
    print(f"V41 START {now} {len(STOCKS)} STOCKS SMALL+MID ONLY")
    found=[]
    for sym in STOCKS:
        r=check(sym)
        if r: found.append(r); print(f"FOUND {r}")
    found=sorted(found, key=lambda x:x['sc'], reverse=True)[:10]
    print(f"Scanned {len(STOCKS)} Found {len(found)}")
    if len(found)==0:
        tg(f"⚡ V41 SMALL+MID SCAN {now.strftime('%H:%M')} | Scanned {len(STOCKS)} | Found 0 Real | 0 Fake Blocked ✅\n9EMA x 15EMA x VWAP + 5m High Vol Bottom/Top\nLargeCap Blocked - Bot Alive")
        return
    tg(f"🚀 V41 SMALL+MID {len(found)} REAL BREAKOUT {now.strftime('%H:%M')} | {len(STOCKS)} STOCKS")
    for st in found:
        sl=st['ltp']*0.99 if st['t']=='BUY' else st['ltp']*1.01
        t1=st['ltp']*1.012 if st['t']=='BUY' else st['ltp']*0.988
        em="🟢 BUY" if st['t']=='BUY' else "🔴 SELL"
        tg(f"{em} {st['s']} @{st['ltp']:.2f} SL {sl:.2f} T1 {t1:.2f} | VWAP {st['vw']}>9EMA {st['e9']}>15EMA {st['e15']} | Vol {st['vx']}x | S:{st['sc']} | SMALL+MID 5m Bottom/Top")

if __name__=="__main__": main()
