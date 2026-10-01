import os, requests, pyotp
from datetime import datetime
from SmartApi import SmartConnect

API_KEY = os.getenv('ANGEL_API_KEY')
CLIENT_ID = os.getenv('ANGEL_CLIENT_ID')
PASSWORD = os.getenv('ANGEL_PASSWORD')
TOTP_SECRET = os.getenv('ANGEL_TOTP_SECRET')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

STOCKS = ["SUNTV", "UNIONBANK", "PFC", "RECLTD", "NBCC", "SUZLON", "TATAPOWER", "IRFC", "SJVN", "IDEA"]

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

def login():
    try:
        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        obj.generateSession(CLIENT_ID, PASSWORD, totp)
        print("Login OK")
        return obj
    except Exception as e:
        print(f"Login Failed: {e}")
        return None

def get_ema(prices, period):
    if len(prices) < period: return None
    ema = sum(prices[:period]) / period
    k = 2 / (period + 1)
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
    return ema

def get_rsi(prices, period=14):
    if len(prices) < period+1: return 50
    gains, losses = 0, 0
    for i in range(1, period+1):
        diff = prices[-i] - prices[-i-1]
        if diff > 0: gains += diff
        else: losses += abs(diff)
    if losses == 0: return 85
    rs = gains / losses
    return 100 - (100 / (1 + rs))

def check_trend(obj):
    buy_list, sell_list = [], []
    for stock in STOCKS:
        try:
      for stock in STOCKS:
        try:
            print(f"Checking {stock}...")
            # इथे तुझा खरा V51 Logic येईल - सध्या Demo साठी Skip करतोय
            # Angel Token List तुझ्या जुन्या File मधून घ्यायचाय

        except Exception as e:
            print(f"{stock} Error {e}")
            continue      
            
        except Exception as e:
            print(f"{stock} Error {e}")
            continue
    return buy_list, sell_list

# --- MAIN ---
print("Scanner Started...")
api = login()
if not api: exit()

buy_list, sell_list = check_trend(api)
now = datetime.now().strftime("%d-%b %I:%M %p IST")

# === फक्त BUY/SELL असेल तरच Message ===
final_msg = ""
if buy_list: final_msg += f"🚀 BUY: {', '.join(buy_list)}\n"
if sell_list: final_msg += f"🔻 SELL: {', '.join(sell_list)}\n"

if final_msg:
    msg = f"""V51 Signal ✅ {now}
{final_msg}
Scanned: {', '.join(STOCKS)}"""
    send_telegram(msg)
    print(f"Sent: {final_msg}")
else:
    print(f"✅ {now} - No BUY/SELL - Telegram Skipped - Checked {len(STOCKS)} stocks")
