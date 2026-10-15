import os, sys, subprocess
for pkg in ["logzero","websocket-client"]:
    try:
        __import__("logzero" if pkg=="logzero" else "websocket")
    except:
        subprocess.check_call([sys.executable,"-m","pip","install",pkg])

import requests, traceback
from datetime import datetime, timedelta

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(msg):
    try:
        base = "https://api.telegram.org/bot"+BOT+"/sendMessage"
        requests.post(base, data={"chat_id":CHAT,"text":msg,"parse_mode":"Markdown"}, timeout=15)
    except: pass
    print(msg)

try:
    from SmartApi import SmartConnect
    import pandas as pd
    import pyotp

    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    totp = pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)

    # Full 50 Liquid List - Nifty +388 साठी Best
    LIST = ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","AXISBANK","SUNPHARMA","TITAN","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","CIPLA","DIVISLAB","TECHM","HCLTECH","GRASIM","ULTRACEMCO","BAJAJFINSV","NESTLEIND","BRITANNIA","EICHERMOT","DRREDDY","HEROMOTOCO","BPCL","INDUSINDBK","M&M","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","SBILIFE","HDFCLIFE","ICICIPRULI","VEDL"]

    ist = datetime.utcnow()+timedelta(hours=5, minutes=30)
    today = ist.strftime("%Y-%m-%d")
    now = ist.strftime("%Y-%m-%d %H:%M")

    sigs = []
    for sym in LIST:
        try:
            sr = obj.searchScrip("NSE", sym)
            if not sr.get("data"): continue
            token = sr["data"][0]["symboltoken"]
            hp = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":today+" 09:15","todate":now}
            cd = obj.getCandleData(hp)
            if not cd.get("data") or len(cd["data"])<15: continue
            df = pd.DataFrame(cd["data"], columns=["time","open","high","low","close","volume"])
            for c in ["close","open","high","low","volume"]: df[c]=pd.to_numeric(df[c])
            df["typ"]=(df["high"]+df["low"]+df["close"])/3
            df["vwap"]=(df["typ"]*df["volume"]).cumsum()/df["volume"].cumsum()
            df["9ema"]=df["close"].ewm(span=9).mean()
            delta=df["close"].diff()
            gain=delta.where(delta>0,0).rolling(14).mean()
            loss=-delta.where(delta<0,0).rolling(14).mean()
            df["rsi"]=100-(100/(1+gain/loss))
            c=df.iloc[-1]
            # Loose Logic for Bull Market - Close > VWAP and RSI >48
            if c["close"]>c["vwap"] and c["close"]>c["open"] and c["rsi"]>48:
                sigs.append((sym,float(c["close"]),float(c["vwap"]),float(c["rsi"])))
        except: continue

    if len(sigs)==0:
        send(f"ℹ️ Checked {len(LIST)} | Nifty +388 Bull पण 3PM नंतर VWAP Flat - उद्या 9:30 AM ला Full Signal @ {ist.strftime('%H:%M')} IST")
    else:
        top=sorted(sigs, key=lambda x: x[3], reverse=True)[:5]
        for sym,ltp,vw,rsi in top:
            txt=f"🟢 *{sym} BUY @ {ltp:.1f}* | Nifty +388 🚀\nClose {ltp:.1f} > VWAP {vw:.1f} | RSI {rsi:.1f}\n\n• NSE Cash BUY\n• NSE 150 Liquid {sym} CE @ 50-90\n• Midcap CE @ 50-90\n• Nifty CE @ 50-90"
            send(txt)

    send(f"✅ Scan Done {len(sigs)}/{len(LIST)} @ {ist.strftime('%H:%M')} IST")
    exit(0)

except Exception as e:
    err=traceback.format_exc()[-700:]
    send(f"Error:\n{err}")
    exit(0) 
