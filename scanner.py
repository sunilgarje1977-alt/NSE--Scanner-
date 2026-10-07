import os, time, requests, pyotp, pytz
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Secrets from GitHub ---
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Telegram ---
def send_tele(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
    except: pass

# --- Angel Login ---
try:
    smart = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()
    smart.generateSession(CLIENT_ID, PASSWORD, totp)
    print("Angel Login OK")
except Exception as e:
    print(f"Login Fail: {e}")
    exit()

# --- BSE 500 Tokens Auto ---
def get_bse500():
    print("Downloading Master...")
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    data = requests.get(url, timeout=20).json()
    bse = [s for s in data if s['exch_seg']=='BSE' and s['symbol'].endswith('-EQ')]
    # Top 500 Active (तू हवे तर इथे तुझी Custom 500 List filter करू शकतो)
    # आता सगळ्यात जास्त Traded 500 घेतो
    return {s['name']: s['token'] for s in bse[:500]}

TOKENS = get_bse500()
print(f"Total Stocks: {len(TOKENS)}")

# --- Scan One Stock ---
def scan_one(item):
    name, token = item
    try:
        # Today Candle
        ist = pytz.timezone('Asia/Kolkata')
        today = datetime.now(ist).strftime("%Y-%m-%d")
        hist = smart.getCandleData({
            "exchange": "BSE",
            "symboltoken": token,
            "interval": "FIVE_MINUTE",
            "fromdate": f"{today} 09:15",
            "todate": f"{today} 15:30"
        })
        if not hist or 'data' not in hist or not hist['data']:
            return None
        df = pd.DataFrame(hist['data'], columns=['time','O','H','L','C','V'])
        if len(df) < 26: return None

        df['VWAP'] = (df['V'] * (df['H']+df['L']+df['C'])/3).cumsum() / df['V'].cumsum()
        df['EMA9'] = df['C'].ewm(span=9).mean()
        df['EMA15'] = df['C'].ewm(span=15).mean()
        df['VAVG'] = df['V'].rolling(20).mean()
        
        delta = df['C'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        c = df.iloc[-1]
        p = df.iloc[-2]

        vol_ok = c['V'] > c['VAVG'] * 1.2
        vwap_up = p['C'] <= p['VWAP'] and c['C'] > c['VWAP']
        vwap_down = p['C'] >= p['VWAP'] and c['C'] < c['VWAP']
        ema_up = p['EMA9'] <= p['EMA15'] and c['EMA9'] > c['EMA15']
        ema_down = p['EMA9'] >= p['EMA15'] and c['EMA9'] < c['EMA15']

        if c['C'] < 30: return None

        # SUPER BUY - तुला हवं असलेलं
        if vwap_up and ema_up and vol_ok and c['RSI'] >= 50:
            return f"🟢 SUPER BUY {name} @ {c['C']:.2f} VOL {c['V']/c['VAVG']:.1f}x RSI{int(c['RSI'])} {today}"

        # SUPER SELL
        if vwap_down and ema_down and vol_ok:
            return f"🔴 SUPER SELL {name} @ {c['C']:.2f} VOL {c['V']/c['VAVG']:.1f}x RSI{int(c['RSI'])} {today}"

    except Exception as e:
        # print(f"{name} err {e}")
        return None
    return None

# --- FAST SCAN 50 Threads ---
signals = []
with ThreadPoolExecutor(max_workers=50) as ex:
    futures = {ex.submit(scan_one, it): it for it in TOKENS.items()}
    for f in as_completed(futures):
        res = f.result()
        if res:
            signals.append(res)
            print(res)
            send_tele(res)

if not signals:
    print("No Signal This Candle")
else:
    print(f"Done: {len(signals)} Signals Sent") 
