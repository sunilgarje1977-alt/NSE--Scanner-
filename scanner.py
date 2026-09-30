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
    print(msg)

def get_15min(smart, token):
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
    last = candles[-1]
    low_15 = float(last[3])
    high_15 = float(last[2])
    close_15 = float(last[4])
    return low_15, high_15, close_15

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

STOCKS = {}
STOCKS["UNIONBANK"] = "15044"
STOCKS["PFC"] = "15315"
STOCKS["RECLTD"] = "13528"
STOCKS["NBCC"] = "115505"
STOCKS["SUZLON"] = "27501"
STOCKS["TCS"] = "11536"
STOCKS["INFY"] = "1594"
STOCKS["RELIANCE"] = "2885"

for sym in STOCKS:
    token = STOCKS[sym]
    ltp = float(smart.ltpData("NSE", sym, token)['data']['ltp'])
    low15, high15, close15 = get_15min(smart, token)
    if ltp >= close15:
        risk = ltp - low15
        if risk < ltp * 0.003:
            risk = ltp * 0.01
        sl = round(low15, 2)
        tgt = round(ltp + risk, 2)
        msg = "BUY " + sym + "\nLTP: " + str(round(ltp,2)) + "\n15M LOW: " + str(low15) + "\nSL: " + str(sl) + "\nTARGET: " + str(tgt)
        send_tg(msg)
    else:
        risk = high15 - ltp
        if risk < ltp * 0.003:
            risk = ltp * 0.01
        sl = round(high15, 2)
        tgt = round(ltp - risk, 2)
        msg = "SELL " + sym + "\nLTP: " + str(round(ltp,2)) + "\n15M HIGH: " + str(high15) + "\nSL: " + str(sl) + "\nTARGET: " + str(tgt)
        send_tg(msg)
