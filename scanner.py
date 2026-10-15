import os, sys, subprocess
# Auto Install - दोन्ही
for pkg in ["logzero", "websocket-client", "smartapi-python", "pyotp", "pandas", "requests"]:
    try:
        __import__(pkg.replace("-", "_").split("-")[0] if pkg!="websocket-client" else "websocket")
    except:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        except:
            pass

import requests, traceback
from datetime import datetime, timedelta

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(msg):
    try:
        base = "https://api.telegram.org/bot" + BOT + "/sendMessage"
        requests.post(base, data={"chat_id": CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except:
        pass
    print(msg)

try:
    from SmartApi import SmartConnect
    import pandas as pd
    import pyotp

    API = os.getenv("ANGEL_API_KEY")
    CODE = os.getenv("ANGEL_CLIENT_ID")
    PWD = os.getenv("ANGEL_PASSWORD")
    TOTP = os.getenv("ANGEL_TOTP_SECRET")

    obj = SmartConnect(api_key=API)
    totp = pyotp.TOTP(TOTP).now()
    obj.generateSession(CODE, PWD, totp)
    send("✅ Login OK - All Modules Fixed!")

    LIST = ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","MARUTI","AXISBANK","TITAN","SUNPHARMA","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL"]

    ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
    today = ist.strftime("%Y-%m-%d")
    now = ist.strftime("%Y-%m-%d %H:%M")

    sigs = []
    checked = 0

    for sym in LIST:
        try:
            sr = obj.searchScrip("NSE", sym)
            if not sr.get("data"): continue
            token = sr["data"][0]["symboltoken"]
            hp = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":today+" 09:15","todate":now}
            cd = obj.getCandleData(hp)
            checked += 1
            if not cd.get("data") or len(cd["data"]) < 15: continue
            df = pd.DataFrame(cd["data"], columns=["time","open","high","low","close","volume"])
            for c in ["close","open","high","low","volume"]: df[c] = pd.to_numeric(df[c])
            df["typ"] = (df["high"]+df["low"]+df["close"])/3
            df["vwap"] = (df["typ"]*df["volume"]).cumsum()/df["volume"].cumsum()
            df["9ema"] = df["close"].ewm(span=9).mean()
            delta = df["close"].diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            df["rsi"] = 100-(100/(1+gain/loss))
            c = df.iloc[-1]
            if c["close"]>c["vwap"] and c["vwap"]>c["9ema"] and c["rsi"]>50:
                sigs.append(sym)
        except:
            continue

    if len(sigs)==0:
        send(f"Checked {checked}/{len(LIST)} | No Signal @ {ist.strftime('%H:%M')} IST")
    else:
        send(f"🟢 BUY: {', '.join(sigs)} | Checked {checked}/{len(LIST)} @ {ist.strftime('%H:%M')} IST")

    exit(0)

except Exception as e:
    err = traceback.format_exc()[-700:]
    send(f"Error:\n{err}")
    exit(0) 
