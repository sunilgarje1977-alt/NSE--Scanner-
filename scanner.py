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
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"HTML"}, timeout=15)
    except Exception as e:
        print(f"Tele Error {e}")

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist)
today_str=now.strftime("%Y-%m-%d")

# Time Check - 9:15 ते 15:15 च्या बाहेर असेल तर बंद
if now.hour < 9 or (now.hour == 9 and now.minute < 15) or now.hour >= 15 and now.minute > 30:
    print(f"Outside Market Hours {now}")
    # exit() # Test साठी चालू ठेवले, उद्या Auto बंद होईल

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

# BSE 500 पूर्ण लिस्ट - 500 Symbols
BSE_500 = ["FSL","NIACL","RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","SBIN","BHARTIARTL","ITC","LT","BAJFINANCE","MARUTI","TATAMOTORS","SUNPHARMA","TITAN","WIPRO","ONGC","NTPC","HCLTECH","POWERGRID","M&M","JSWSTEEL","HINDALCO","CIPLA","DIVISLAB","TATASTEEL","TECHM","ADANIENT","ADANIPORTS","AXISBANK","KOTAKBANK","TATAPOWER","RECLTD","PFC","IRCTC","HAL","BEL","BANKBARODA","PNB","FEDERALBNK","AUBANK","DLF","GODREJPROP","INDIGO","DMART","ZOMATO","IRFC","RVNL","SAIL","VEDL","POLYCAB","PERSISTENT","COFORGE","DIXON","HAVELLS","SIEMENS","ABB","BSE","CDSL","TRENT","SRF","TVSMOTOR","MOTHERSON","PIDILITIND","DABUR","SBILIFE","HDFCLIFE","ICICIGI","HUDCO","CONCOR","COCHINSHIP","BDL","IOC","GAIL","BPCL","LICI","GICRE","YESBANK","IDEA","HFCL","SUZLON","BHEL","MAZDOCK","GRSE","NBCC","JPOWER","KPIGREEN","JPPOWER","GMRINFRA","ADANIPOWER","ADANIGREEN","ATGL","AMBUJACEM","ACC","ULTRACEMCO","SHREECEM","JKCEMENT","GRASIM","HINDZINC","COALINDIA","OIL","IGL","MGL","PETRONET","JSWENERGY","TORNTPOWER","CESC","BAJAJ-AUTO","HEROMOTOCO","TVSMOTOR","EICHERMOT","M&M","MARUTI","ASHOKLEY","BHARATFORG","MOTHERSON","SONACOMS","UNOMINDA","BALKRISIND","MRF","APOLLOTYRE","SUNPHARMA","DRREDDY","CIPLA","LUPIN","AUROPHARMA","ZYDUSLIFE","DIVISLAB","BIOCON","SYNGENE","NESTLEIND","BRITANNIA","MARICO","GODREJCP","HINDUNILVR","VBL","TATACONSUM","TRENT","ABFRL","PAGEIND","TITAN","KALYANKJIL","BATA","CAMPUS","INDIGO","JIOFIN","INDUSTOWER","TATACOMM","TEJASNET","TATATECH","LTIM","LTTS","KPITTECH","TATAELXSI","BSOFT","COFORGE","PERSISTENT","MPHASIS","FIRSTSOURCE","INTELLECT","ANGELONE","MCX","IEX","NUVAMA","LTF","MUTHOOTFIN","MANAPPURAM","PAYTM","NYKAA","DELHIVERY","INDIAMART","AFFLE","TANLA","ROUTE","KPRMILL","VEDANTFASH","SAFARI","SENCOS","THANGAMAYL","RELAXO","METROBRAND","NHPC","SJVN","IRB","NCC","NBCC","PNCINFRA","GRINFRA","KNRCON","ASHOKA","ADANIPOWER","TATACOMM","HFCL","STERLITE","TATAPOWER","TORNTPOWER","NTPCGREEN","IREDA","NHPC","SJVN","HUDCO","NLCINDIA","COALINDIA","HINDCOPPER","NATIONALUM","VEDL","HINDALCO","SAIL","TATASTEEL","JSWSTEEL","JINDALSTEL","NMDC","NMDCSTEEL","JSL","JSWENERGY","ADANIGREEN","KPI","SUZLON","INOXWIND","INOXGREEN","TATATECH","KPIT","TATACOMM","FSL","INTELLECT","BSOFT","COFORGE","PERSISTENT","MPHASIS","LTIM","HCLTECH","TCS","INFY","WIPRO","TECHM","LTTS","TATAELXSI","TATACOMM","360ONE","MOTILALOFS","ANANDRATHI","KFINTECH","CAMS","UTIAMC","HDFCAMC","NAM-INDIA","ABSLAMC","SBILIFE","HDFCLIFE","ICICIPRULI","STARHEALTH","SBICARD","BAJAJFINSV","CHOLAFIN","SHRIRAMFIN","M&MFIN","POONAWALLA","BAJAJHLDNG","BAJAJFINSV","POWERGRID","TATAPOWER","ADANITRANS","POWERINDIA","ABB","SIEMENS","HAVELLS","POLYCAB","KEI","RRKABEL","CGPOWER","BHEL","BEML","HAL","BEL","BDL","MAZDOCK","GRSE","COCHINSHIP","BEML","LTF","MUTHOOT","MANAPPURAM","GOLDBEES","SILVERBEES","BSE","CDSL","MCX","IEX","NSE","LICHSGFIN","PNBHOUSING","CANFINHOME","AAVAS","APTUS","HOMEFIRST","SBILIFE","HDFCLIFE","ICICIGI","GICRE","NIACL","STARHEALTH","TATACONSUM","MARICO","DABUR","COLPAL","EMAMI","BAJAJCON","HONASA","NYKAA","DMART","TRENT","ABFRL","RAYMOND","PAGEIND","KPRMILL","VEDANTFASH","SAFARI","TITAN","KALYANKJIL","SENCOS","THANGAMAYL","BATAINDIA","RELAXO","METROBRAND","CAMPUS","INDIGO","SPICEJET","INTERGLOBE","IRCTC","TATACOMM","BHARTIARTL","JIOFIN","IDEA","INDUSTOWER","TATACOMM","HFCL","TATATECH","LTIM","LTTS","KPITTECH","TATAELXSI","TATACOMM","FSL","INTELLECT","BSOFT","COFORGE","PERSISTENT","MPHASIS","FIRSTSOURCE","ANGELONE","MCX","IEX","NUVAMA","LTF","MUTHOOTFIN","MANAPPURAM","PAYTM","NYKAA","DELHIVERY","INDIAMART","AFFLE","TANLA","ROUTE","TATACONSUM","VBL","TITAN","KALYANKJIL","BATA","CAMPUS","IRB","NHPC","SJVN","HUDCO","NCC","ADANIGREEN","ATGL","ACC","AMBUJACEM","SHREECEM","JKCEMENT","GRASIM","HINDZINC","COALINDIA","OIL","IGL","MGL","PETRONET","NTPC","TORNTPOWER","CESC","BAJAJ-AUTO","HEROMOTOCO","EICHERMOT","ASHOKLEY","BHARATFORG","SONACOMS","UNOMINDA","BALKRISIND","MRF","SUNPHARMA","DRREDDY","CIPLA","LUPIN","AUROPHARMA","ZYDUSLIFE","DIVISLAB","BIOCON","SYNGENE"]
BSE_500 = list(dict.fromkeys(BSE_500)) # duplicate काढले

def get_token(sym):
    try:
        r=smart.searchScrip("NSE", sym)
        if r and r['data']: return sym, r['data'][0]['symboltoken']
    except: pass
    return sym, None

print(f"Finding tokens for {len(BSE_500)}...")
tokens={}
with ThreadPoolExecutor(max_workers=25) as ex:
    futs=[ex.submit(get_token,s) for s in BSE_500]
    for f in as_completed(futs):
        s,t=f.result()
        if t: tokens[s]=t
print(f"Tokens Found: {len(tokens)}")

def scan(item):
    name, token=item
    try:
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
        pct=(curr['C']-first['O'])/first['O']*100
        vol_ratio=curr['V']/curr['VOLAVG'] if curr['VOLAVG']>0 else 1

        # V7 ON-TIME CONDITION - हाच FSL सारखा Breakout पकडेल
        if curr['C']>curr['EMA9'] and curr['C']>curr['EMA21'] and curr['C']>curr['VWAP'] and curr['RSI']>=60 and vol_ratio>=1.2 and curr['C']>prev['H'] and pct>=1.0:
            return ("BUY", pct, f"🚀 <b>{name}</b> BREAKOUT @ {curr['C']:.1f}\n+{pct:.1f}% RSI:{int(curr['RSI'])} Vol:{vol_ratio:.1f}x ⏰{now.strftime('%H:%M')}")

        # Early Trend
        if curr['C']>curr['EMA9'] and curr['RSI']>=57 and curr['C']>curr['VWAP'] and pct>=0.7 and vol_ratio>=1.0:
            return ("BUY", pct, f"🟢 <b>{name}</b> @ {curr['C']:.1f} +{pct:.1f}% RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}")

    except: return None

buys=[]
with ThreadPoolExecutor(max_workers=30) as ex:
    for f in as_completed({ex.submit(scan,it):it for it in tokens.items()}):
        r=f.result()
        if r: buys.append(r)

buys=sorted(buys, key=lambda x: x[1], reverse=True)[:10]

if buys:
    msg=f"⚡️ <b>BSE 500 ON-TIME {now.strftime('%d-%b %H:%M:%S')}</b>\n9:15-3:15 Active - {len(tokens)} Stocks\n\n" + "\n\n".join([x[2] for x in buys])
    send_tele(msg)
else:
    send_tele(f"⏳ {now.strftime('%H:%M')} BSE 500 - No Breakout - {len(tokens)} Checked") 
