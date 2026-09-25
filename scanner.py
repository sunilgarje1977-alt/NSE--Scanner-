import yfinance as yf
import requests
import os
import pytz
from datetime import datetime
from SmartApi import SmartConnect
import pyotp

# CONFIG - Strict Filters
BREAKOUT_THRESHOLD = 0.4  # <-- 0.8 चा 0.4 केला
MIN_PRICE = 80
MIN_VOLUME_RATIO = 1.5
RSI_MIN = 55
RSI_MAX = 75

# NSE Stocks List
STOCKS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","KOTAKBANK","LT","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","WIPRO","ULTRACEMCO","BAJFINANCE","HCLTECH","POWERGRID","NTPC","ONGC","TATAMOTORS","JSWSTEEL","TATASTEEL","ADANIENT","COALINDIA","HINDALCO","GRASIM","BPCL","EICHERMOT","DRREDDY","CIPLA","DIVISLAB","BRITANNIA","HEROMOTOCO","APOLLOHOSP","BAJAJFINSV","TECHM","INDUSINDBK","SPORTKING","GSFC","XTRANET","TARAPUR"]

def get_angel_client():
    try:
        api_key = os.getenv("ANGEL_API_KEY")
        client_id = os.getenv("ANGEL_CLIENT_ID")
        pwd = os.getenv("ANGEL_PASSWORD")
        totp_secret = os.getenv("ANGEL_TOTP_SECRET")
        if not all([api_key, client_id, pwd, totp_secret]):
            return None
        totp = pyotp.TOTP(totp_secret).now()
        obj = SmartConnect(api_key=api_key)
        data = obj.generateSession(client_id, pwd, totp)
        return obj
    except Exception as e:
        print(f"Angel Login Fail: {e}")
        return None

def send_telegram(msg):
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": msg})
    except Exception as e:
        print(f"Telegram Fail: {e}")

def scan():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).strftime("%H:%M")
    active_count = 0
    results = []
    
    angel = get_angel_client()
    
    for stock in STOCKS:
        try:
            df = yf.download(stock + ".NS", period="5d", interval="15m", progress=False)
            if len(df) < 20:
                continue
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            price = float(last['Close'])
            if price < MIN_PRICE:
                continue
            
            # Breakout % Check - 0.4%
            breakout = ((last['Close'] - last['Open']) / last['Open']) * 100
            if abs(breakout) < BREAKOUT_THRESHOLD:
                continue
            
            # Volume Check
            vol_ratio = last['Volume'] / df['Volume'].tail(20).mean()
            if vol_ratio < MIN_VOLUME_RATIO:
                continue
            
            results.append(f"{stock} {breakout:+.2f}% ₹{price:.0f}")
            active_count += 1
            
            # Order Place Logic (if Angel connected)
            if angel and breakout > 0:
                try:
                    # angel.placeOrder(...) # Your order logic
                    pass
                except:
                    pass

        except Exception as e:
            continue
    
    msg = f"Scan {now} Active:{active_count}/2 Done:0/6\n"
    if results:
        msg += "\n".join(results[:10])
    else:
        msg += "No breakout > 0.4%"

    print(msg)
    send_telegram(msg)

if __name__ == "__main__":
    scan()
