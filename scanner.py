import os, requests, pyotp
import pandas as pd
from SmartApi import SmartConnect
from datetime import datetime

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

def calc_rsi(closes, period=14):
    try:
        delta = pd.Series(closes).diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi.iloc[-1], 2)
    except:
        return 50

def get_15m_data(smart, token):
    try:
        now = datetime.now()
        start = now.replace(hour=9, minute=0, second=0, microsecond=0)
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIFTEEN_MINUTE",
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": now.strftime("%Y-%m-%d %H:%M")
        }
        resp = smart.getCandleData(params)
        candles = resp.get('data', [])
        if len(candles) < 20:
            return None
        closes = [float(c[4]) for c in candles]
        rsi = calc_rsi(closes)
        prev = candles[-2]
        last = candles[-1]
        return {
            "rsi": rsi,
            "prev_high": float(prev[2]),
            "prev_low": float(prev[3]),
            "today_low": min([float(c[3]) for c in candles]),
            "today_high": max([float(c[2]) for c in candles]),
            "closes": closes
        }
    except Exception as e:
        print(f"Candle Error {e}")
        return None

print("Login...")
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

STOCKS = [
    {"sym": "UNIONBANK", "token": "15044", "name": "UNIONBANK-EQ"},
    {"sym": "PFC", "token": "15315", "name": "PFC-EQ"},
    {"sym": "RECLTD", "token": "13528", "name": "RECLTD-EQ"},
    {"sym": "NBCC", "token": "115505", "name": "NBCC-EQ"},
    {"sym": "SUZLON", "token": "27501", "name": "SUZLON-EQ"},
    {"sym": "TCS", "token": "11536", "name": "TCS-EQ"},
]

for s in STOCKS:
    try:
        ltp_resp = smart.ltpData("NSE", s["name"], s["token"])
        ltp = float(ltp_resp['data']['ltp'])
        data = get_15m_data(smart, s["token"])
        if not data:
            continue

        rsi = data["rsi"]
        # --- FINAL CONDITION ---
        # BUY: Breakout + RSI > 60
        if ltp > data["prev_high"] and rsi > 60:
            sl = data["prev_low"]
            risk = ltp - sl
            if risk < ltp*0.005: risk = ltp*0.01
            tgt = ltp + risk*1.5
            send_tg(f"BUY {s['sym']}\nLTP: {ltp:.2f}\nRSI: {rsi} (>60)\n15M High
