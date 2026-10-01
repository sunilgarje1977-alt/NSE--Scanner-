import os, pyotp
from SmartApi import SmartConnect
import requests

API_KEY = os.getenv('ANGEL_API_KEY','').strip()
CLIENT_ID = os.getenv('ANGEL_CLIENT_ID','').strip()
PASSWORD = os.getenv('ANGEL_PASSWORD','').strip()
TOTP_SECRET = os.getenv('ANGEL_TOTP_SECRET','').strip()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN','').strip()
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID','').strip()

STOCKS = ["SUNTV", "UNIONBANK", "MUTHOOTFIN"] # तुझी List इथे टाक

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
            print(f"Checking {stock}...")
            # तुझा खरा V51 Logic इथे येईल
        except Exception as e:
            print(f"{stock} Error {e}")
            continue
    return buy_list, sell_list

# --- Main ---
try:
    totp = pyotp.TOTP(TOTP_SECRET).now()
    smartApi = SmartConnect(API_KEY)
    data = smartApi.generateSession(CLIENT_ID, PASSWORD, totp)
    print("Login OK")
    b, s = check_trend(smartApi)
    if not b and not s:
        print("✅ No BUY/SELL - Telegram Skipped")
    else:
        msg = ""
        if b: msg += "🚀 BUY: " + ", ".join(b) + "\n"
        if s: msg += "🔻 SELL: " + ", ".join(s) + "\n"
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
        print("Signal Sent")
except Exception as e:
    print(f"Login/Main Error {e}")
