# V44 LIVE - Angel One + 1:1 Trailing BUY/SELL - FINAL FIX
import os, time, requests, pyotp
from SmartApi import SmartConnect

# --- FIX: .strip() लावल्याने \n Error जाणार ---
API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","").strip()
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","").strip()

SL_PER = 0.06  # 6% = 1:1

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg}, timeout=15)
        print(f"Sent: {msg[:50]}")
    except Exception as e:
        print(f"TG Error: {e}")

def get_levels(ltp, side):
    ltp=float(ltp)
    if side=="BUY":
        sl=round(ltp*(1-SL_PER),2)
        tgt=round(ltp*(1+SL_PER),2)
    else:
        sl=round(ltp*(1+SL_PER),2)
        tgt=round(ltp*(1-SL_PER),2)
    return sl, sl, tgt

print("V44 Angel Login...")
try:
    smart = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()
    session = smart.generateSession(CLIENT_ID, PASSWORD, totp)
    print("Angel Login Success ✅")
except Exception as e:
    err = f"V44 Angel Login Fail: {e}"
    print(err)
    send_tg(err)
    exit()

# NSE Stocks with Angel Tokens
STOCKS = {
    "NBCC": "115505", "SUZLON": "27501", "HAL": "13650", "IOC": "13266",
    "DLF": "15557", "RELIANCE": "14977", "TCS": "18457", "INFY": "15921",
    "UNIONBANK": "15044", "RECLTD": "13528", "PFC": "15315", "NCC": "11422"
}

buy_list=[]; sell_list=[]

for sym, token in STOCKS.items():
    try:
        data = smart.ltpData("NSE", sym, token)
        ltp = float(data['data']['ltp'])
        print(f"{sym} LTP: {ltp}")
        sl, tsl, tgt = get_levels(ltp, "BUY")
        buy_list.append((sym, ltp, sl, tsl, tgt))
        time.sleep(0.4)
    except Exception as e:
        print(f"{sym} Error: {e}")
        continue

buy_list = buy_list[:6]

if not buy_list:
    send_tg("V44 LIVE 30-09 - No BUY Setup (Angel Running ✅)")
else:
    for sym, ltp, sl, tsl, tgt in buy_list:
        msg = f"🟢 BUY {sym} - TOP 6\nLTP: {ltp:.2f}\nSL: {sl}\nTSL: {tsl}\nTARGET: {tgt}\nRR: 1:1 Trailing"
        send_tg(msg)

print("V44 Done")
