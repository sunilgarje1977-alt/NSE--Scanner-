import os, requests, pyotp, pytz
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY=os.getenv("ANGEL_API_KEY")
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID")
PASSWORD=os.getenv("ANGEL_PASSWORD")
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")

def send_tele(msg):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"HTML"}, timeout=10)

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist)
today_str=now.strftime("%Y-%m-%d")

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

# BSE 500 - तुझा FSL पण आहे
SYMBOLS = ["FSL","NIACL","RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","SBIN","BHARTIARTL","ITC","LT","BAJFINANCE","MARUTI","TATAMOTORS","SUNPHARMA","TITAN","WIPRO","ONGC","HCLTECH","POWERGRID","M&M","JSWSTEEL","HINDALCO","TATASTEEL","TECHM","ADANIENT","ADANIPORTS","AXISBANK","KOTAKBANK","TATAPOWER","RECLTD","PFC","IRCTC","HAL","BEL","BANKBARODA","PNB","FEDERALBNK","DLF","INDIGO","DMART","ZOMATO","IRFC","RVNL","SAIL","VEDL","POLYCAB","BSE","CDSL","TRENT","TVSMOTOR","MOTHERSON","SBILIFE","HUDCO","CONCOR","BDL","IOC","GAIL","BPCL","LICI","YESBANK","IDEA","HFCL","SUZLON","BHEL","MAZDOCK","COCHINSHIP","GRSE","NBCC","JPOWER","KPIGREEN","JPPOWER","GMRINFRA","ADANIPOWER","TATAELXSI","LTTS","KPITTECH","TATATECH","INTELLECT","BSOFT","COFORGE","PERSISTENT","MPHASIS","FIRSTSOURCE","ANGELONE","MCX","IEX","NUVAMA","LTF","MUTHOOTFIN","MANAPPURAM","PAYTM","NYKAA","DELHIVERY","INDIAMART","AFFLE","TANLA","ROUTE","TEJASNET","TATACOMM","HEXAWARE","TATACONSUM","VBL","TITAN","KALYANKJIL","BATA","CAMPUS","IRB","NHPC","SJVN","HUDCO","NCC","ADANIGREEN","ATGL","ACC","AMBUJACEM","SHREECEM","JKCEMENT","GRASIM","HINDZINC","COALINDIA","OIL","IGL","MGL","PETRONET","NTPC","TORNTPOWER","CESC","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","ASHOKLEY","BHARATFORG","SONACOMS","UNOMINDA","BALKRISIND","MRF","SUNPHARMA","DRREDDY","CIPLA","LUPIN","AUROPHARMA","ZYDUSLIFE","DIVISLAB","BIOCON","SYNGENE","NESTLEIND","BRITANNIA","DABUR","MARICO","GODREJCP","HINDUNILVR","DMART","TRENT","ABFRL","PAGEIND","TITAN","INDIGO","JIOFIN","INDUSTOWER","JETAIRWAYS","TATACOMM"]

def get_token(sym):
    try:
        r=smart.searchScrip("NSE", sym)
        if r['data']: return sym, r['data'][0]['symboltoken']
    except: pass
    return sym, None

tokens={}
with ThreadPoolExecutor(max_workers=20) as ex:
    for f in as_completed([ex.submit(get_token,s) for s in SYMBOLS]):
        s,t=f.result()
        if t: tokens[s]=t

def scan(item):
    name, token=item
    try:
        # 1 MINUTE Candle - हाच On-Time चा Secret
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_MINUTE","fromdate":f"{today_str} 09:15","todate":f"{today_str} 15:30"})
        if not hist or 'data' not in hist or len(hist['data'])<20: return None
        df=pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V'])
        df['EMA9']=df['C'].ewm(span=9).mean()
        df['EMA21']=df['C'].ewm(span=21).mean()
        df['VWAP']=(df['V']*(df['H']+df['L']+df['C'])/3).cumsum()/df['V'].cumsum()
        df['VOLAVG']=df['V'].rolling(20).mean()
        d=df['C'].diff()
        df['RSI']=100-(100/(1+d.where(d>0,0).rolling(9).mean()/-d.where(d<0,0).rolling(9).mean().replace(0,0.01)))

        curr=df.iloc[-1]
        prev=df.iloc[-2]
        first=df.iloc[0]

        # FSL Chart सारखा Logic
        day_pct=(curr['C']-first['O'])/first['O']*100
        vol_ratio=curr['V']/curr['VOLAVG'] if curr['VOLAVG']>0 else 1

        # ON-TIME CONDITION - Candle Close होताच Trigger
        # तुझ्या Chart मध्ये 09:20 ला: Price > White Line (EMA9), Yellow (EMA21), RSI 76, Volume मोठा - तोच हा
        if curr['C']>curr['EMA9'] and curr['C']>curr['EMA21'] and curr['C']>curr['VWAP'] and curr['RSI']>62 and vol_ratio>1.4 and curr['C']>prev['H']:
            return f"🚀 <b>{name} BREAKOUT</b> @ {curr['C']:.1f}\n+{day_pct:.2f}% | RSI:{int(curr['RSI'])} | Vol:{vol_ratio:.1f}x | {now.strftime('%H:%M:%S')} - ON TIME"

        # Early Trend - 09:15 लाच
        if day_pct>=0.8 and curr['C']>curr['EMA9'] and curr['RSI']>58 and curr['C']>curr['VWAP']:
            return f"🟢 <b>{name}</b> @ {curr['C']:.1f} +{day_pct:.1f}% RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}"

    except: return None

results=[]
with ThreadPoolExecutor(max_workers=30) as ex:
    for f in as_completed({ex.submit(scan,it):it for it in tokens.items()}):
        r=f.result()
        if r: results.append(r)

if results:
    msg=f"⚡️ <b>ON-TIME SCAN {now.strftime('%H:%M:%S')}</b> - BSE 500\n\n" + "\n\n".join(results[:12])
    send_tele(msg)
else:
    # Sideways असेल तर Message नको, फक्त Breakout ला पाठव
    pass
