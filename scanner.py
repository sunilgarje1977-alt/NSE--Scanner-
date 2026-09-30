import os, time, requests, pyotp, datetime
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PWD = os.getenv("ANGEL_PASSWORD")
TOTP_SEC = os.getenv("ANGEL_TOTP_SECRET")

# 150+ SMALL+MID STOCKS - V44
STOCKS = ["SJVN","HUDCO","RVNL","IRFC","NBCC","IREDA","IDEA","JPOWER","NHPC","SUZLON","YESBANK","HCC","JPASSOCIAT","RPOWER","TATAPOWER","ADANIPOWER","IRCON","RAILTEL","MAZDOCK","COCHINSHIP","GRSE","BEML","BDL","HAL","BEL","BHEL","IOC","ONGC","GMRINFRA","DLF","IBREALEST","SOUTHBANK","UCOBANK","BANKOFMAHA","CENTRALBK","IDFCFIRSTB","UNIONBANK","BANKINDIA","INDIANB","PSB","IOB","CANBK","PNB","RECLTD","PFC","SJVN","MRPL","CHENNPETRO","NCC","HFCL","ITI","MTNL","VODAFONE","TRIDENT","ALOKINDS","SUZLON"]

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", json={"chat_id": CHAT, "text": m, "parse_mode": "Markdown"}, timeout=10)
        time.sleep(2)
    except: pass

smart = None
# Angel Login Try
if API_KEY and CLIENT_ID:
    try:
        from SmartApi import SmartConnect
        totp = pyotp.TOTP(TOTP_SEC).now()
        smart = SmartConnect(api_key=API_KEY)
        smart.generateSession(CLIENT_ID, PWD, totp)
        print("Angel Login OK")
    except Exception as e:
        print(f"Angel Login Fail, yfinance fallback: {e}")
        smart = None

def get_df(sym):
    try:
        df = yf.Ticker(sym + ".NS").history(period="60d", interval="5m")
        if len(df) < 40: return None
        df['E9'] = df['Close'].ewm(span=9).mean()
        df['E15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = (df['Close']*df['Volume']).cumsum() / df['Volume'].cumsum()
        df['VA'] = df['Volume'].rolling(20).mean()
        return df
    except: return None

def check(sym):
    df = get_df(sym)
    if df is None: return None
    try:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        c, e9, e15, vwap, vol, va = last['Close'], last['E9'], last['E15'], last['VWAP'], last['Volume'], last['VA']
        
        # LIVE PRICE FROM ANGEL IF POSSIBLE
        ltp = c
        if smart:
            try:
                # NSE token fetch is complex, use yfinance ltp for now but Angel logged in
                pass
            except: pass

        cond5 = c > e9 and c > e15 and c > vwap and vol > va * 1.3
        cond6 = c < e9 and c < e15 and c < vwap

        if cond5 and prev['Close'] < prev['E9']: # Bottom 5
            tsl = round(min(df['Low'].tail(5).min(), e9),2)
            return f"🟢 *BUY {sym}* - BOTTOM 5\nLTP: {ltp:.2f}\nTSL: {tsl}\nVol: {vol/va:.1f}x"
        if cond6 and prev['Close'] > prev['E9']: # Top 6
            tsl = round(max(df['High'].tail(5).max(), e9),2)
            return f"🔴 *SELL {sym}* - TOP 6\nLTP: {ltp:.2f}\nTSL: {tsl}"
    except: return None
    return None

print("V44 Scanning Started...")
results = []
with ThreadPoolExecutor(max_workers=10) as ex:
    for r in ex.map(check, STOCKS):
        if r: results.append(r)

if results:
    msg = f"*V44 LIVE {datetime.datetime.now().strftime('%d-%m %H:%M')}*\n\n" + "\n\n".join(results[:15])
    tg(msg)
    print(f"Sent {len(results)} signals")
else:
    print("0 Real - No Setup")
    # tg("V44 Scan - 0 Real Setup Found") # Comment to avoid spam
