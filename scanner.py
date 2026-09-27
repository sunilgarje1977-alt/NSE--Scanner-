import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime, timedelta
from SmartApi import SmartConnect

def clean(k):
    return os.getenv(k,"").strip().strip('"').strip("'")

API_KEY = clean('ANGEL_API_KEY')
CLIENT_ID = clean('ANGEL_CLIENT_ID')
PWD = clean('ANGEL_PASSWORD')
TOTP_SECRET = clean('ANGEL_TOTP_SECRET')
TELE_TOKEN = clean('TELEGRAM_BOT_TOKEN')
TELE_CHAT = clean('TELEGRAM_CHAT_ID')

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())

def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        requests.get(url, params={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except:
        pass

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", "scrip_master.json")

with open("scrip_master.json") as f:
    master = json.load(f)

token_map = {s['name']: s['token'] for s in master if s['exch_seg'] == 'NSE' and s['symbol'].endswith('-EQ')}

def get_patterns(df):
    if len(df) < 3:
        return []
    c1 = df.iloc[-3]
    c2 = df.iloc[-2]
    c = df.iloc[-1]
    pats = []
    body = abs(c['Close'] - c['Open'])
    if body == 0:
        body = 0.1
    low_wick = min(c['Open'], c['Close']) - c['Low']
    up_wick = c['High'] - max(c['Open'], c['Close'])
    if low_wick > body * 2 and up_wick < body * 0.5:
        pats.append("HAMMER")
    if up_wick > body * 2 and low_wick < body * 0.5:
        pats.append("INV_HAMMER")
    if c2['Close'] < c2['Open'] and c['Close'] > c['Open'] and c['Close'] > c2['Open'] and c['Open'] < c2['Close']:
        pats.append("BULL_ENGULF")
    if c2['Close'] > c2['Open'] and c['Close'] < c['Open'] and c['Open'] > c2['Close'] and c['Close'] < c2['Open']:
        pats.append("BEAR_ENGULF")
    if c1['Close'] < c1['Open'] and abs(c2['Close'] - c2['Open']) < c2['Close'] * 0.02 and c['Close'] > c['Open']:
        pats.append("MORNING_STAR")
    if c1['Close'] > c1['Open'] and abs(c2['Close'] - c2['Open']) < c2['Close'] * 0.02 and c['Close'] < c['Open']:
        pats.append("EVENING_STAR")
    if c1['Close'] > c1['Open'] and c2['Close'] > c2['Open'] and c['Close'] > c['Open']:
        pats.append("3_WHITE")
    if c1['Close'] < c1['Open'] and c2['Close'] < c2['Open'] and c['Close'] < c['Open']:
        pats.append("3_BLACK")
    return pats

def get_movers():
    try:
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        g = s.get("https://www.nseindia.com/api/live-analysis-variations?index=gainers", headers=headers, timeout=5).json()
        l = s.get("https://www.nseindia.com/api/live-analysis-variations?index=losers", headers=headers, timeout=5).json()
        gain = [x['symbol'] for x in g['NIFTY']['data'][:40]] if 'NIFTY' in g else []
        lose = [x['symbol'] for x in l['NIFTY']['data'][:40]] if 'NIFTY' in l else []
        if gain:
            return gain + lose
    except:
        pass
    return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","HAL","BEL","RVNL","NHPC","PFC","RECLTD","IRFC","TATASTEEL","ITC","LT","SBIN","TATAPOWER","ZOMATO","POWERGRID","KDDL","NITCO","GREENPANEL"]

def analyze(sym):
    try:
        token = token_map.get(sym)
        if not token:
            return None
        fromdate = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        todate = datetime.now().strftime("%Y-%m-%d %H:%M")
        data = smart.getCandleData({"exchange": "NSE", "symboltoken": token, "interval": "FIFTEEN_MINUTE", "fromdate": fromdate, "todate": todate})['data']
        df = pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        if len(df) < 40:
            return None
        ltp = df['Close'].iloc[-1]
        if ltp < 20:
            return None
        if df['Volume'].iloc[-1] < 10000:
            return None
        df['EMA9'] = df['Close'].ewm(9).mean()
        df['EMA15'] = df['Close'].ewm(15).mean()
        df['TP'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['VWAP'] = (df['TP'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss = (-delta.clip(upper=0)).ewm(alpha=1
