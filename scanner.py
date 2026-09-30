# V44 FINAL - 15 MIN Candle Low SL + BUY/SELL 1:1
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

def get_15min(smart, token):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=2)
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIFTEEN_MINUTE", # 15 MIN
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }
        data = smart.getCandleData(params)
        candles = data['data']
        if not candles: return None, None
        last = candles[-1] # [ts, open, high, low, close]
        low_15 = float(last[3])
        high_15 = float(last[2])
        close_15 = float(last[4])
        return low_15, high_15, close_15
    except Exception as e:
        print(f"Candle Error {e}")
        return None, None, None

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

STOCKS = {
    "UNIONBANK": "15044", "PFC": "15315", "RECLTD": "13528",
    "NBCC": "115505", "SUZLON": "27501", "TCS": "11536",
    "INFY": "1594", "RELIANCE": "2885"
}

for sym, token in STOCKS.items():
    try:
        ltp = float(smart.ltpData("NSE", sym, token)['data']['ltp'])
        low15, high15, close15 = get_15min(smart, token)
        if not low15: continue

        # BUY Condition: LTP > 15min Close
        if ltp >= close15:
            risk = ltp - low15
            if risk < ltp*0.003: risk = ltp*0.01 # Min 0.3% to 1% filter
            sl = round(low15, 2)
            tgt = round(ltp + risk, 2)
            send_tg(f"🟢 BUY {sym}\nLTP: {ltp:.2f}\n15M
