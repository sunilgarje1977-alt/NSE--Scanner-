import os, requests, pyotp
from SmartApi import SmartConnect
from datetime import datetime
import time

API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","").strip()
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()

def send_tg(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        print(text)
    except Exception as e:
        print(f"TG Error {e}")

def calc_rsi_simple(closes, period=14):
    if len(closes) < period+1: return 50
    gains, losses = 0, 0
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
        if diff > 0: gains += diff
        else: losses -= diff
    if losses == 0: return 80
    rs = gains / losses
    return 100 - (100 / (1 + rs))

def get_15m(smart, token):
    try:
        now = datetime.now()
        start = now.replace(hour=9, minute=15, second=0, microsecond=0)
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIFTEEN_MINUTE",
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": now.strftime("%Y-%m-%d %H:%M")
        }
        data = smart.getCandleData(params).get('data', [])
        if len(data) < 15: return None
        closes = [float(c[4]) for c in data]
        rsi = calc_rsi_simple(closes)
        prev = data[-2]
        return {"rsi": rsi, "prev_high": float(prev[2]), "prev_low": float(prev[3])}
    except Exception as e:
        print(f"Candle Err {e}")
        return None

print("Login...")
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

STOCKS = [
    ["UNIONBANK", "15044", "UNIONBANK-EQ"],
    ["PFC", "15315", "PFC-EQ"],
    ["RECLTD", "13528", "RECLTD-EQ"],
    ["NBCC", "115505", "NBCC-EQ"],
    ["SUZLON", "27501", "SUZLON-EQ"],
]

found = False
for sym, token, eq in STOCKS:
    try:
        time.sleep(1) # Angel la 1 sec gap de - Block honar nahi
        ltp = float(smart.ltpData("NSE", eq, token)['data']['ltp'])
        d = get_15m(smart, token)
        if not d: continue
        print(f"{sym} LTP:{ltp} RSI:{d['rsi']:.1f}")

        if ltp > d["prev_high"] and d["rsi"] > 60:
            sl = d["prev_low"]
            tgt = ltp + (ltp - sl)*1.5
            send_tg(f"BUY {sym}\nLTP: {ltp:.2f}\nRSI: {d['rsi']:.1f} >60\nSL: {sl:.2f} (15M Low)\nTARGET: {tgt:.2f}")
            found = True
        elif ltp < d["prev_low"] and d["rsi"] < 50:
            sl = d["prev_high"]
            tgt = ltp - (sl - ltp)*1.5
            send_tg(f"SELL {sym}\nLTP: {ltp:.2f}\nRSI: {d['rsi']:.1f} <50\nSL: {sl:.2f} (15M High)\nTARGET: {tgt:.2f}")
            found = True
    except Exception as e:
        print(f"{sym} Error {e}")

if not found:
    send_tg("V47 Scanner - No Signal - RSI Filter Active (BUY>60 SELL<50)")

print("Done")
