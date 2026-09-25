import yfinance as yf
import requests, os, pytz, pyotp
from datetime import datetime
from SmartApi import SmartConnect

# === ON TIME CONFIG ===
BREAKOUT = 0.4  # तुझं 0.4%
MIN_PRICE = 80
VOL_RATIO = 1.2  # On time साठी थोडं कमी केलं
STOCKS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","MARUTI","TITAN","SUNPHARMA","BAJFINANCE","TATAMOTORS","ADANIENT","POWERGRID","NTPC","ONGC","SPORTKING","GSFC","XTRANET"]

def send_tg(msg):
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id":chat_id,"text":msg}, timeout=10)
    except: pass

def scan():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist).strftime("%H:%M:%S")
    found = []
    for s in STOCKS:
        try:
            df = yf.download(s+".NS", period="1d", interval="1m", progress=False, auto_adjust=True)
            if len(df) < 20: continue
            last = df.iloc[-1]
            price = float(last['Close'])
            if price < MIN_PRICE: continue
            
            # On Time Breakout - 1 min candle
            bo = ((last['Close'] - last['Open']) / last['Open']) * 100
            if abs(bo) < BREAKOUT: continue
            
            # Volume
            vr = last['Volume'] / df['Volume'].tail(20).mean()
            if vr < VOL_RATIO: continue

            found.append(f"{s} {bo:+.2f}% ₹{price:.0f} Vol{vr:.1f}x")
        except: continue

    if found:
        msg = f"⚡ ON TIME SCAN {now}\n" + "\n".join(found[:8])
    else:
        msg = f"Scan {now} No Trade >0.4% (1m)"
    
    print(msg)
    send_tg(msg)

if __name__ == "__main__":
    scan()
