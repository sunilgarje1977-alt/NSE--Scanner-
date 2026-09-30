# V44 FINAL FIXED - 15 MIN Low SL - No Syntax Error
import os, requests, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta

API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","").strip()
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()

def send_tg(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print(msg)
    except Exception as e:
        print(f"TG Fail {e}")

def get_15min(smart, token):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=2)
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIFTEEN_MINUTE",
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }
        data = smart.getCandleData(params)
        candles = data['data']
        if not candles:
            return None, None, None
        last = candles[-1]
        low_15 = float(last[3])
        high_15 = float(last[2])
        close_15 = float(last[4])
        return low_15, high_15, close_15
    except Exception as e:
        print(f"Candle Error {e}")
        return None, None, None

print("Login...")
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

STOCKS = {
    "UNIONBANK": "15044",
    "PFC": "15315",
    "RECLTD": "13528",
    "NBCC": "115505",
    "SUZLON": "27501",
    "TCS": "11536
