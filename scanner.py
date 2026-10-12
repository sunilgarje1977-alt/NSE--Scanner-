import os, requests, pyotp, pytz
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# Secrets
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_tele(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except:
        pass

ist = pytz.timezone('Asia/Kolkata')
now = datetime.now(ist)
today_str = now.strftime("%Y-%m-%d")

# Login
try:
    smart = SmartConnect(api_key=API_KEY)
    smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
except Exception as e:
    send_tele(f"❌ Login Fail: {e}")
    exit()

# 100 Most Active Stocks - NIACL Add केलंय
TOKENS = {
"RELIANCE":"2885","TCS":"11536","HDFCBANK":"1333","ICICIBANK":"4963","INFY":"1594","SBIN":"3045","BHARTIARTL":"10604","ITC":"1660","LT":"11483","BAJFINANCE":"317","MARUTI":"10999","TATAMOTORS":"3456","SUNPHARMA":"3350","TITAN":"3506","ULTRACEMCO":"11532","WIPRO":"3787","ONGC":"2475","NTPC":"11630","HCLTECH":"7229","POWERGRID":"14977","M&M":"2031","JSWSTEEL":"11723","HINDALCO":"1363","CIPLA":"694","DIVISLAB":"10940","TATASTEEL":"3499","TECHM":"13538","ADANIENT":"25","ADANIPORTS":"15083","AXISBANK":"5900","KOTAKBANK":"1922","JSWENERGY":"12127","TATAPOWER":"3426","NHPC":"9418","RECLTD":"15332","PFC":"15543","IRCTC":"13849","HAL":"23087","BEL":"148","BANKBARODA":"4668","PNB":"7178","FEDERALBNK":"1023","AUBANK":"24463","DLF":"14732","GODREJPROP":"10099","INDIGO":"11184","DMART":"14035","ZOMATO":"26121","IRFC":"23115","RVNL":"25562","SAIL":"1260","VEDL":"3063","NMDC":"11483","POLYCAB":"23957","PERSISTENT":"19237","COFORGE":"11543","DIXON":"17094","HAVELLS":"981","SIEMENS":"3150","ABB":"1","BSE":"22533","CDSL":"20840","TRENT":"1964","SRF":"3155","TVSMOTOR":"3518","MOTHERSON":"4204","PIDILITIND":"6819","DABUR":"772","SBILIFE":"21808","HDFCLIFE":"467","ICICIGI":"18663","LICHSGFIN":"12828","HUDCO":"19357","CONCOR":"4307","COCHINSHIP":"19844","BDL":"23136","IOC":"1624","GAIL":"665","BPCL":"526","NIACL":"15482","LICI":"15379","GICRE":"15438","NHPC":"9418","SJVN":"11373","IRB":"13611","HFCL":"3140","IDEA":"14366","YESBANK":"305","BANKBARODA":"4668","CANBK":"7041","UNIONBANK":"11868","IDFCFIRSTB":"11287"
}

def scan_stock(item):
    name, token = item
    try:
        hist = smart.getCandleData({
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIVE_MINUTE",
            "fromdate": f"{today_str} 09:15",
            "todate": f"{today_str} 15:30"
        })
        if not hist or 'data' not in hist or len(hist['data']) < 25:
            return None

        df = pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V'])

        # Indicators
        df['EMA9'] = df['C'].ewm(span=9).mean()
        df['EMA21'] = df['C'].ewm(span=21).mean()
        df['VWAP'] = (df['V']*(df['H']+df['L']+df['C'])/3).cumsum() / df['V'].cumsum()
        df['VOLAVG'] = df['V'].rolling(20).mean()

        # RSI
        d = df['C'].diff()
        gain = d.where(d>0,0).rolling(14).mean()
        loss = -d.where(d<0,0).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss.replace(0,0.01)))

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        if curr['C'] < 25: return None

        vol_ratio = curr['V'] / curr['VOLAVG'] if curr['VOLAVG'] > 0 else 1
        is_high_vol = vol_ratio >= 1.15

        # ON-TIME LOGIC
        # BUY Condition
        if curr['C'] > curr['EMA9'] and curr['EMA9'] > curr['EMA21'] and curr['C'] > curr['VWAP']:
            if curr['RSI'] > 55 and is_high_vol:
                tag = "🚀 BREAKOUT" if curr['C'] > prev['H'] else "🟢 TREND"
                return ("BUY", curr['RSI'], f"{tag} <b>{name}</b> @ {curr['C']:.2f}\nRSI:{curr['RSI']:.0f} | Vol:{vol_ratio:.1f}x | {now.strftime('%H:%M')}")

        # SELL Condition
        if curr['C'] < curr['EMA9'] and curr['EMA9'] < curr['EMA21'] and curr['C'] < curr['VWAP']:
            if curr['RSI'] < 45 and is_high_vol:
                return ("SELL", curr['RSI'], f"🔴 <b>{name}</b> @ {curr['C']:.2f}\nRSI:{curr['RSI']:.0f} | Vol:{vol_ratio:.1f}x | {now.strftime('%H:%M')}")

    except:
        return None

# Run
buys, sells = [], []
with ThreadPoolExecutor(max_workers=30) as ex:
    futs = {ex.submit(scan_stock, it): it for it in TOKENS.items()}
    for f in as_completed(futs):
        res = f.result()
        if res:
            if res[0] == "BUY": buys.append(res)
            else: sells.append(res)

buys = sorted(buys, key=lambda x: x[1], reverse=True)[:8]
sells = sorted(sells, key=lambda x: x[1])[:8]

# Telegram Send
if buys or sells:
    header = f"📈 <b>On-Time Scan {now.strftime('%d-%b %H:%M')}</b> ({len(TOKENS)} stocks)\n\n"
    body = ""
    for _,_,m in buys: body += m + "\n\n"
    for _,_,m in sells: body += m + "\n\n"
    send_tele(header + body)
else:
    send_tele(f"⏳ {now.strftime('%H:%M')} - No Setup ({len(TOKENS)} checked) - Sideways Market")  
