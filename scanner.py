# V44 LIVE - Candle Low SL + 1:1 Target
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
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=10)

def get_candle_low_smart(smart, token):
    try:
        # शेवटच्या 1 दिवसाच्या 5 मिनिटाच्या Candle
        to_date = datetime.now()
        from_date = to_date - timedelta(days=2)
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIVE_MINUTE",
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }
        data = smart.getCandleData(params)
        candles = data['data']
        if not candles: return None, None
        last_candle = candles[-1] # [timestamp, open, high, low, close, volume]
        candle_low = float(last_candle[3])
        candle_high = float(last_candle[2])
        ltp = float(last_candle[4])
        return ltp, candle_low, candle_high
    except:
        return None, None, None

print("Angel Login...")
smart = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
smart.generateSession(CLIENT_ID, PASSWORD, totp)
print("Login Success ✅")

STOCKS = {
    "NBCC": "115505", "SUZLON": "27501", "HAL": "13650", "IOC": "13266",
    "TCS": "30207", "UNIONBANK": "15044", "RECLTD": "13528", "PFC": "15315"
}

for sym, token in STOCKS.items():
    try:
        ltp, low, high = get_candle_low_smart(smart, token)
        if not ltp: continue

        # --- BUY: SL = Candle Low, TARGET = 1:1 ---
        risk = ltp - low
        if risk <= 0: continue

        sl = round(low, 2)
        target = round(ltp + risk, 2) # 1:1
        tsl = sl

        msg = f"🟢 BUY {sym} - TOP 6\nLTP: {ltp:.2f}\nCandle LOW: {low:.2f}\nSL: {sl} (Candle Low)\nTSL: {tsl}\nTARGET: {target}\nRR: 1:1"
        send_tg(msg)
        print(msg)

    except Exception as e:
        print(f"{sym} Error {e}")
