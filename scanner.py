import os
import requests
import traceback
from datetime import datetime, timedelta

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

def send(msg):
    try:
        base = "https://api.telegram.org/bot"
        base = base + BOT + "/sendMessage"
        requests.post(base, data={
            "chat_id": CHAT,
            "text": msg,
            "parse_mode": "Markdown"
        }, timeout=15)
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

    if not API:
        send("Secrets Missing")
        exit(0)

    # Login
    obj = SmartConnect(api_key=API)
    totp = pyotp.TOTP(TOTP).now()
    obj.generateSession(CODE, PWD, totp)

    # List - 30 Stocks - Fast
    LIST = [
        "RELIANCE","TCS","HDFCBANK","ICICIBANK",
        "INFY","BHARTIARTL","SBIN","BAJFINANCE",
        "ITC","LT","KOTAKBANK","MARUTI",
        "AXISBANK","SUNPHARMA","TITAN","WIPRO",
        "NTPC","POWERGRID","ONGC","TATAMOTORS",
        "TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS",
        "COALINDIA","HINDALCO","CIPLA","DIVISLAB",
        "TECHM","HCLTECH"
    ]

    ist = datetime.utcnow()
    ist = ist + timedelta(hours=5, minutes=30)
    today = ist.strftime("%Y-%m-%d")
    now = ist.strftime("%Y-%m-%d %H:%M")

    sigs = []
    checked = 0

    for sym in LIST:
        try:
            sr = obj.searchScrip("NSE", sym)
            if not sr.get("data"):
                continue
            token = sr["data"][0]["symboltoken"]
            hp = {
                "exchange": "NSE",
                "symboltoken": token,
                "interval": "FIVE_MINUTE",
                "fromdate": today + " 09:15",
                "todate": now
            }
            cd = obj.getCandleData(hp)
            checked = checked + 1
            if not cd.get("data"):
                continue
            if len(cd["data"]) < 15:
                continue

            df = pd.DataFrame(
                cd["data"],
                columns=["time","open","high","low","close","volume"]
            )
            for col in ["close","open","high","low","volume"]:
                df[col] = pd.to_numeric(df[col])

            df["typ"] = (df["high"]+df["low"]+df["close"])/3
            df["vwap"] = (df["typ"]*df["volume"]).cumsum()
            df["vwap"] = df["vwap"]/df["volume"].cumsum()
            df["9ema"] = df["close"].ewm(span=9).mean()

            delta = df["close"].diff()
            gain = delta.where(delta>0,0).rolling(14).mean()
            loss = -delta.where(delta<0,0).rolling(14).mean()
            df["rsi"] = 100-(100/(1+gain/loss))

            c = df.iloc[-1]
            p = df.iloc[-2]

            # Nifty +388 Bull Logic
            bull = c["close"]>c["vwap"]
            bull = bull and c["vwap"]>c["9ema"]
            bull = bull and c["close"]>c["open"]
            bull = bull and c["rsi"]>50

            if bull:
                cross = p["vwap"]<=p["9ema"] and c["vwap"]>c["9ema"]
                score = 10 if cross else 6
                sigs.append((sym,c["close"],c["vwap"],c["9ema"],c["rsi"],score))

        except Exception as e:
            print(sym, e)
            continue

    if len(sigs)==0:
        send(f"Checked {checked}/{len(LIST)} | Nifty Bull +388 | No Tight Cross @ {ist.strftime('%H:%M')} IST")
    else:
        top = sorted(sigs, key=lambda x: x[5], reverse=True)[:4]
        for s in top:
            sym,ltp,vw,em,rsi,sc = s
            txt = f"BUY {sym} @ {ltp:.1f}\n"
            txt = txt + f"VWAP {vw:.1f} > 9EMA {em:.1f} RSI {rsi:.1f}\n"
            txt = txt + f"Checked {checked}/{len(LIST)}"
            send("🟢 " + txt)

    print("Done Success")
    exit(0)

except Exception as e:
    err = traceback.format_exc()
    err = err[-600:]
    send(f"Error But Success:\n{err}")
    print(err)
    exit(0)  
