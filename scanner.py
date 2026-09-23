import os, pyotp, requests, time
from SmartApi import SmartConnect
import pandas as pd

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# NSE 1000 Stocks - तुझी 1000 ची list
NSE_1000 = [
"RELIANCE-EQ","TCS-EQ","INFY-EQ","HDFCBANK-EQ","ICICIBANK-EQ","SBIN-EQ","BHARTIARTL-EQ","ITC-EQ","KOTAKBANK-EQ","LT-EQ",
"AXISBANK-EQ","ASIANPAINT-EQ","MARUTI-EQ","BAJFINANCE-EQ","HCLTECH-EQ","WIPRO-EQ","ULTRACEMCO-EQ","TITAN-EQ","SUNPHARMA-EQ","NESTLEIND-EQ"
# इथे अजून 980 add करू शकतोस - मी 1000 ची full list तयार करून देईन
]

def get_ltp_smartapi(obj, symbol):
    try:
        # Angel ला token लागतो, सोप्यासाठी search करून घेतो
        res = obj.searchScrip("NSE", symbol.replace("-EQ",""))
        if res and res['data']:
            token = res['data'][0]['symboltoken']
            ltp = obj.ltpData("NSE", symbol.replace("-EQ",""), token)
            return ltp['data']['ltp']
    except:
        return None
    return None

def scan():
    totp = pyotp.TOTP(TOTP_SECRET).now()
    obj = SmartConnect(api_key=API_KEY)
    session = obj.generateSession(CLIENT_ID, PASSWORD, totp)

    results = "📊 NSE 1000 Scanner (Angel):\n\n"
    count = 0

    for sym in NSE_1000[:100]: # आधी 100 टेस्ट करू, नंतर 1000 करू
        price = get_ltp_smartapi(obj, sym)
        if price:
            results += f"{sym} - Rs.{price}\n"
            count += 1
        time.sleep(0.2)
        if count >= 50: # Telegram ला 50 एका वेळी
            break

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": results})
    print(f"Scanned {count} stocks")

if __name__ == "__main__":
    scan()
