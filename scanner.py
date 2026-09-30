import os, requests, pyotp
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

def get_today_15m(smart, token):
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
        if len(candles) < 2:
            return None
        # candles: [timestamp, open, high, low, close, volume]
        prev_candle = candles[-2]
        last_candle = candles[-1]
        return {
            "prev_high": float(prev_candle[2]),
            "prev_low": float(prev_candle[3]),
            "prev_close": float(prev_candle[4]),
            "last_low": float(last_candle[3]),
            "last_high": float(last_candle[2]),
            "today_low": min([float(c[3]) for c in candles]),
            "today_high": max([float(c[2]) for c in candles])
        }
    except Exception as e:
        print(f"Candle Error {e}")
        return None

print("Angel Login...")
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login Success")

# NSE Correct Tokens with EQ name
STOCKS = [
    {"sym": "UNIONBANK", "token": "15044", "name": "UNIONBANK-EQ"},
    {"sym": "PFC", "token": "15315", "name": "PFC-EQ"},
    {"sym": "RECLTD", "token": "13528", "name": "RECLTD-EQ"},
    {"sym": "NBCC", "token": "115505", "name": "NBCC-EQ"},
    {"sym": "SUZLON", "token": "27501", "name": "SUZLON-EQ"},
    {"sym": "TCS", "token": "11536", "name": "TCS-EQ"},
    {"sym": "INFY", "token": "1594", "name": "INFY-EQ"},
    {"sym": "RELIANCE", "token": "2885", "name": "RELIANCE-EQ"},
]

buy_signals = []
sell_signals = []

for s in STOCKS:
    try:
        # LIVE LTP - Correct Method
        ltp_resp = smart.ltpData(s["name"], "NSE", s["token"])
        # Angel returns in different format, handle both
        if 'data' in ltp_resp and 'ltp' in ltp_resp['data']:
            ltp = float(ltp_resp['data']['ltp'])
        else:
            ltp = float(ltp_resp['data']['ltp'])

        c = get_today_15m(smart, s["token"])
        if not c:
            continue

        # --- NEW LOGIC ---
        # BUY: LTP breaks previous 15M High
        if ltp > c["prev_high"]:
            sl = c["prev_low"]
            risk = ltp - sl
            if risk < ltp * 0.005:
                risk = ltp * 0.01
                sl = ltp - risk
            target = ltp + (risk * 1.5)
            buy_signals.append(f"BUY {s['sym']}\nLTP: {ltp:.2f}\n15M Breakout: {c['prev_high']:.2f}\nSL: {sl:.2f} (15M Low)\nTARGET: {target:.2f}\nRR: 1:1.5")

        # SELL: LTP breaks previous 15M Low
        elif ltp < c["prev_low"]:
            sl = c["prev_high"]
            risk = sl - ltp
            if risk < ltp * 0.005:
                risk = ltp * 0.01
                sl = ltp + risk
            target = ltp - (risk * 1.5)
            sell_signals.append(f"SELL {s['sym']}\nLTP: {ltp:.2f}\n15M Breakdown: {c['prev_low']:.2f}\nSL: {sl:.2f} (15M High)\nTARGET: {target:.2f}\nRR: 1:1.5")

    except Exception as e:
        print(f"{s['sym']} Error {e}")

# Send TOP 6
for msg in buy_signals[:6]:
    send_tg(msg)
for msg in sell_signals[:6]:
    send_tg(msg)

if not buy_signals and not sell_signals:
    send_tg("V45 Scanner - No Breakout Today - Market Sideways")
