import os, requests, pyotp, time
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
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=15)
        print(f"TG Status: {r.status_code} | {r.text[:300]}")
    except Exception as e:
        print(f"TG Error: {e}")

def calc_rsi(closes, period=14):
    if len(closes) < period+1: return 50
    g=l=0
    for i in range(1, period+1):
        diff = closes[-i] - closes[-i-1]
        if diff>0: g+=diff
        else: l-=diff
    if l==0: return 70
    return 100 - (100/(1+g/l))

print("=== V48 START ===")
print("Login...")
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

today = datetime.now()
# Sunday Test
if today.weekday() >= 5:
    send_tg(f"✅ V48 Bot Working!\nDate: {today.strftime('%d-%b %A')}\nMarket Closed Today.\nToken Error Fixed!\nLogin OK!\nMonday पासून BUY/SELL Signal चालू होतील!")
    print("Sunday - Test msg sent")
    exit()

STOCKS = ["UNIONBANK", "PFC", "RECLTD", "NBCC", "SUZLON"]
found = False

for sym in STOCKS:
    try:
        time.sleep(1)
        print(f"\nSearching {sym}...")
        search = smart.searchScrip("NSE", sym)
        if not search.get('data'):
            print(f"{sym} Not Found")
            continue

        # पहिलाच result घे
        token = search['data'][0]['symboltoken']
        tradingsym = search
