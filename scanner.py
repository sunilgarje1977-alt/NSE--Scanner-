import os, requests, pyotp, pytz
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd

# Secrets
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tele(msg):
    print(msg) # log मध्ये दिसेल
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=15)
        print(f"Telegram Response: {r.text}")
    except Exception as e:
        print(f"Telegram Error: {e}")

ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist)
today_str = now.strftime("%Y-%m-%d")

# 1. पहिला Message - हाच येत नाही तर Secret चुकलंय
send_tele(f"✅ <b>Scanner Started {now.strftime('%H:%M:%S')}</b>\nTesting Telegram...")

# Login
try:
    smart = SmartConnect(api_key=API_KEY)
    smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
    send_tele(f"✅ Angel Login Success")
except Exception as e:
    send_tele(f"❌ Login Fail: {e}")
    exit()

# फक्त 20 Stock - BSE 500 नको, आधी Message येतोय का बघू
TOKENS = {
"FSL": "5305", "NIACL": "15482", "RELIANCE": "2885", "TCS": "11536", "HDFCBANK": "1333",
"ICICIBANK": "4963", "INFY": "1594", "SBIN": "3045", "BHARTIARTL": "10604", "ITC": "1660",
"BEL": "148", "HAL": "23087", "BSE": "22533", "SUZLON": "12119", "BHEL": "438",
"MAZDOCK": "20831", "RVNL": "25562", "IRFC": "23115", "ZOMATO": "26121", "TATAPOWER": "3426"
}

found=[]
for name, token in TOKENS.items():
    try:
        hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today_str} 09:15","todate":f"{today_str} 15:30"})
        if not hist or 'data' not in hist or len(hist['data'])<10: continue
        df = pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V'])
        curr = df.iloc[-1]
        first = df.iloc[0]
        pct = (curr['C']-first['O'])/first['O']*100

        # सोपं Logic - सगळे Stock दाखवेल, On-Time Test साठी
        if pct>0:
            found.append(f"🟢 {name} @ {curr['C']:.1f} +{pct:.2f}%")
        else:
            found.append(f"🔴 {name} @ {curr['C']:.1f} {pct:.2f}%")
    except Exception as e:
        print(f"{name} error {e}")

if found:
    msg = f"📊 <b>BSE Scan {now.strftime('%H:%M:%S')} - {len(found)} Stocks</b>\n\n" + "\n".join(found[:15])
    send_tele(msg)
else:
    send_tele(f"⏳ {now.strftime('%H:%M:%S')} - Data नाही मिळाला - Market बंद आहे का?")
