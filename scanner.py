import os, sys, subprocess
for pkg in ["logzero","websocket-client"]:
    try:
        __import__("logzero" if pkg=="logzero" else "websocket")
    except:
        subprocess.check_call([sys.executable,"-m","pip","install",pkg])

import requests, traceback, math
from datetime import datetime, timedelta

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(msg):
    try:
        base = "https://api.telegram.org/bot"+BOT+"/sendMessage"
        requests.post(base, data={"chat_id":CHAT,"text":msg,"parse_mode":"Markdown"}, timeout=15)
    except: pass
    print(msg)

def get_strike(price, typ="CE"):
    # Strike Interval Logic
    if price < 500:
        step = 10
    elif price < 1000:
        step = 20
    elif price < 2000:
        step = 20
    elif price < 5000:
        step = 50
    else:
        step = 100

    atm = round(price / step) * step

    if typ == "CE":
        # Bull - OTM 1 and 2
        otm1 = atm + step
        otm2 = atm + step*2
        best = otm1
        # 50-90 premium logic: approx 1-2% OTM
        if price > 1000:
            best = atm + step*2
    else:
        # Bear - PE OTM
        otm1 = atm - step
        otm2 = atm - step*2
        best = otm1
        if price > 1000:
            best = atm - step*2

    return atm, best, step

try:
    from SmartApi import SmartConnect
    import pandas as pd
    import pyotp

    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    totp = pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)

    LIST = ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","AXISBANK","SUNPHARMA","TITAN","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","CIPLA","DIVISLAB","TECHM","HCLTECH","GRASIM","ULTRACEMCO","BAJAJFINSV","NESTLEIND","BRITANNIA","EICHERMOT","DRREDDY","HEROMOTOCO","BPCL","INDUSINDBK","M&M","APOLLOHOSP","TATACONSUM","BAJAJ-AUTO","SBILIFE","HDFCLIFE","VEDL"]

    ist = datetime.utcnow()+timedelta(hours=5, minutes=30)
    today = ist.strftime("%Y-%m-%d")
    now = ist.strftime("%Y-%m-%d %H:%M")

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
            p=df.iloc[-2]

            # BUY Signal
            if c["close"]>c["vwap"] and c["vwap"]>c["9ema"] and c["rsi"]>48 and c["close"]>c["open"]:
                atm, best, step = get_strike(float(c["close"]), "CE")
                msg = f"🟢 *{sym} BUY @ {c['close']:.1f}* | Nifty +388\n"
                msg += f"Close {c['close']:.1f} > VWAP {c['vwap']:.1f} | RSI {c['rsi']:.1f}\n\n"
                msg += f"💥 *CE Strike:*\n"
                msg += f"• ATM: {atm} CE\n"
                msg += f"• *Best OTM: {best} CE* (Premium 50-90 Target)\n"
                msg += f"• Logic: {best-atm} Point OTM | Step {step}\n\n"
                msg += f"• NSE Cash BUY\n• Nifty CE 50-90\n• Midcap CE 50-90"
                send(msg)

            # SELL Signal
            if c["close"]<c["vwap"] and c["vwap"]<c["9ema"] and c["rsi"]<48 and c["close"]<c["open"]:
                atm, best, step = get_strike(float(c["close"]), "PE")
                msg = f"🔴 *{sym} SELL @ {c['close']:.1f}* | Bear\n"
                msg += f"Close {c['close']:.1f} < VWAP {c['vwap']:.1f} | RSI {c['rsi']:.1f}\n\n"
                msg += f"💥 *PE Strike:*\n"
                msg += f"• ATM: {atm} PE\n"
                msg += f"• *Best OTM: {best} PE* (Premium 50-90 Target)\n\n"
                msg += f"• Cash SELL\n• Nifty PE Put Buy"
                send(msg)

        except: continue

    send(f"✅ Scan Done {len(LIST)} @ {ist.strftime('%H:%M')} IST")
    exit(0)

except Exception as e:
    err=traceback.format_exc()[-700:]
    send(f"Error:\n{err}")
    exit(0)
