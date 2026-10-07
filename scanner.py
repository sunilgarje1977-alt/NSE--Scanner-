import os, requests, pyotp, pytz
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tele(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist)
send_tele(f"🚀 BSE 500 Scanner Started {now.strftime('%H:%M')}")

# Login
try:
    smart = SmartConnect(api_key=API_KEY)
    totp = pyotp.TOTP(TOTP_SECRET).now()
    smart.generateSession(CLIENT_ID, PASSWORD, totp)
    print("Login OK")
except Exception as e:
    send_tele(f"❌ Login Fail {e}")
    exit()

# Tokens
def get_tokens():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    data = requests.get(url, timeout=20).json()
    bse = [s for s in data if s['exch_seg']=='BSE' and s['symbol'].endswith('-EQ')][:500]
    return {s['name']: s['token'] for s in bse}

TOKENS = get_tokens()

def scan_one(item):
    name, token = item
    try:
        today = now.strftime("%Y-%m-%d")
        hist = smart.getCandleData({"exchange":"BSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:15","todate":f"{today} 15:30"})
        if not hist or 'data' not in hist or not hist['data']: return None
        df = pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V'])
        if len(df) < 26: return None
        df['VWAP'] = (df['V'] * (df['H']+df['L']+df['C'])/3).cumsum() / df['V'].cumsum()
        df['EMA9'] = df['C'].ewm(9).mean()
        df['EMA15'] = df['C'].ewm(15).mean()
        df['VAVG'] = df['V'].rolling(20).mean()
        d = df['C'].diff()
        df['RSI'] = 100 - (100 / (1 + (d.where(d>0,0).rolling(14).mean() / -d.where(d<0,0).rolling(14).mean())))
        c=df.iloc[-1]; p=df.iloc[-2]
        if c['C']<30: return None
        vol_ok = c['V'] > c['VAVG']*1.2
        vwap_up = p['C']<=p['VWAP'] and c['C']>c['VWAP']
        vwap_down = p['C']>=p['VWAP'] and c['C']<c['VWAP']
        ema_up = p['EMA9']<=p['EMA15'] and c['EMA9']>c['EMA15']
        ema_down = p['EMA9']>=p['EMA15'] and c['EMA9']<c['EMA15']

        if vwap_up and ema_up and vol_ok and c['RSI']>=50:
            return f"🟢 SUPER BUY {name} @ {c['C']:.2f} VOL {c['V']/c['VAVG']:.1f}x RSI{int(c['RSI'])}"
        if vwap_down and ema_down and vol_ok and c['RSI']<=50:
            return f"🔴 SUPER SELL {name} @ {c['C']:.2f} VOL {c['V']/c['VAVG']:.1f}x RSI{int(c['RSI'])}"
    except: return None

sigs=[]
with ThreadPoolExecutor(max_workers=40) as ex:
    futs = {ex.submit(scan_one, it): it for it in TOKENS.items()}
    for f in as_completed(futs):
        r=f.result()
        if r: sigs.append(r)

if sigs:
    for s in sigs: 
        print(s)
        send_tele(s)
else:
    send_tele(f"ℹ️ Checked {len(TOKENS)} - No BUY/SELL at {now.strftime('%H:%M')}") 
