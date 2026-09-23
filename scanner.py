import os
import requests
import pyotp
from SmartApi import SmartConnect
from datetime import datetime

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

def send(msg):
    url = f"https://api.telegram.org/bot{BOT}/sendMessage"
    requests.post(url, data={"chat_id": CHAT, "text": msg, "parse_mode": "Markdown"})

try:
    totp = pyotp.TOTP(TOTP_SECRET).now()
    api = SmartConnect(api_key=API_KEY)
    api.generateSession(CLIENT_ID, PASSWORD, totp)

    stocks = [
        ("RELIANCE-EQ", "2885"),
        ("TCS-EQ", "11536"),
        ("INFY-EQ", "1594"),
        ("HDFCBANK-EQ", "1333")
    ]

    msg = f"📊 *Angel Scanner*\n{datetime.now().strftime('%d-%m %H:%M')}\n\n"

    for sym, token in stocks:
        data = api.ltpData("NSE", sym, token)
        ltp = data['data']['ltp']
        msg += f"{sym}: Rs {ltp}\n"

    msg += "\n✅ Angel Live"
    send(msg)
    print(msg)

except Exception as e:
    send(f"❌ Error: {e}")
    print(e)
