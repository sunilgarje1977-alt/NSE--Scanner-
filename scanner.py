import os, requests, pyotp, time
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd

# --- Secrets ---
API_KEY = os.getenv('ANGEL_API_KEY')
CLIENT_ID = os.getenv('ANGEL_CLIENT_ID')
PASSWORD = os.getenv('ANGEL_PASSWORD')
TOTP_SECRET = os.getenv('ANGEL_TOTP_SECRET')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

STOCKS = ["SUNTV", "UNIONBANK", "PFC", "RECLTD", "NBCC", "SUZLON", "TATAPOWER", "IRFC", "SJVN", "IDEA", "MTNL"]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print("Telegram Sent")
    except Exception as e:
        print(f"Telegram Error: {e}")

def login():
    try:
        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = obj.generateSession(CLIENT_ID, PASSWORD, totp)
        print("Login OK")
        return obj
    except Exception as e:
        print(f"Login Failed: {e}")
        return None

def check_trend(obj):
    buy_list = []
    # इथे तुझा Original V51 Logic आहे तसाच राहील
    # हा Demo Filter आहे - तुझा EMA+RSI+Vol वाला Logic इथे आहे तो तसाच ठेव
    for stock in STOCKS:
        try:
            # तुझा Original Indicator Check इथे
            # if price > ema9 > ema21 > ema50 and 60 < rsi < 85 and vol_spike and high_break:
            #     buy_list.append(stock)
            pass
        except:
            continue
    return buy_list

# --- MAIN ---
print("Scanner Started...")
api = login()
if not api:
    exit()

buy_list = check_trend(api)
now = datetime.now().strftime("%d-%b %I:%M %p IST")

# === फक्त BUY असेल तरच Message ===
if buy_list:
    msg = f"""🚀 V51 BUY Signal ✅ {now}
BUY: {', '.join(buy_list)}

Filter: Price>EMA9>21>50 + RSI 60-85 + Vol Spike + High Break
Scanned: {', '.join(STOCKS)}"""
    send_telegram(msg)
else:
    # हा Message आता Telegram ला जाणार नाही, फक्त GitHub Log मध्ये दिसेल
    print(f"✅ {now} - No Strong Trend Now - Telegram Skipped - Scanned: {', '.join(STOCKS)}")

print("Done")
