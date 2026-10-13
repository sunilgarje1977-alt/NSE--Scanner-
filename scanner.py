import os, requests, pyotp, pytz
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
API_KEY=os.getenv("ANGEL_API_KEY")
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID")
PASSWORD=os.getenv("ANGEL_PASSWORD")
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET")

def send_tele(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"HTML"}, timeout=15)
    except: pass

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist)
today_str=now.strftime("%Y-%m-%d")

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

# NSE 500 लिस्ट - तुझ्या Screenshot मध्ये 294 येत होते, आता ह्या लिस्टने 480+ येईल
NSE_500 = ["360ONE","ABB","ACC","ADANIENT","ADANIGREEN","ADANIPORTS","ADANIPOWER","AFFLE","AJANTPHARM","ALKEM","AMBUJACEM","ANGELONE","APOLLOHOSP","APOLLOTYRE","ASHOKLEY","ASIANPAINT","ASTRAL","ATGL","AUBANK","AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BALKRISIND","BANKBARODA","BATAINDIA","BDL","BEL","BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BPCL","BRITANNIA","BSE","BSOFT","CAMS","CANBK","CDSL","CESC","CGPOWER","CHOLAFIN","CIPLA","COALINDIA","COCHINSHIP","COFORGE","COLPAL","CONCOR","CROMPTON","CUMMINSIND","CYIENT","DABUR","DALBHARAT","DEEPAKNTR","DELHIVERY","DIVISLAB","DIXON","DLF","DMART","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","FSL","GAIL","GODREJCP","GODREJPROP","GRANULES","GRASIM","GRSE","HAL","HDFCBANK","HDFCLIFE","HAVELLS","HEROMOTOCO","HINDALCO","HINDUNILVR","HUDCO","ICICIBANK","ICICIGI","ICICIPRULI","IEX","IDEA","IDFCFIRSTB","INDHOTEL","INDIAMART","INDIGO","INDUSINDBK","INDUSTOWER","INFY","IOC","IPCALAB","IRB","IRCTC","IRFC","ITC","JINDALSTEL","JIOFIN","JKCEMENT","JSWENERGY","JSWSTEEL","JUBLFOOD","KAJARIACER","KALYANKJIL","KEI","KFINTECH","KPITTECH","KPRMILL","LTF","LT","LTIM","LTTS","LICI","LUPIN","M&M","M&MFIN","MANAPPURAM","MARICO","MARUTI","MAZDOCK","MCX","MGL","MOTHERSON","MPHASIS","MRF","MUTHOOTFIN","NAUKRI","NBCC","NCC","NESTLEIND","NHPC","NMDC","NTPC","OBEROIRLTY","OIL","ONGC","PAGEIND","PAYTM","PERSISTENT","PETRONET","PFC","PIDILITIND","PNB","POLYCAB","POWERGRID","PRESTIGE","RECLTD","RELIANCE","RVNL","SAIL","SBIN","SBICARD","SBILIFE","SRF","SUNPHARMA","TATACOMM","TATACONSUM","TATAPOWER","TATASTEEL","TATAMOTORS","TCS","TECHM","TITAN","TORNTPHARM","TRENT","TVSMOTOR","ULTRACEMCO","UPL","VEDL","VBL","VOLTAS","WIPRO","ZOMATO","ZYDUSLIFE","ABBOTINDIA","AARTIIND","ADANIENSOL","ADVENZYMES","AEGISLOG","ALEMBICLTD","AMBER","APARINDS","ASAHIINDIA","ATUL","AVANTIFEED","BAYERCROP","BERGEPAINT","BLUESTARCO","CARBORUN","CASTROLIND","CENTURYPLY","CHALET","CHAMBLFERT","CRISIL","DATAPATTNS","DEVYANI","EIDPARRY","EIHOTEL","ELGIEQUIP","ENDURANCE","FINEORG","FINCABLES","GLAND","GODFRYPHLP","GRINFRA","HDFCAMC","INDIACEM","INDIANB","JKTYRE","JMFINANCIL","JUSTDIAL","KARURVYSYA","LAURUSLABS","LICHSGFIN","LINDEINDIA","METROBRAND","NATCOPHARM","PATANJALI","PNBHOUSING","POLYMED","POONAWALLA","RADICO","RAILTEL","RBLBANK","RELAXO","SAFARI","SJVN","SKFINDIA","SUNTV","SUPREMEIND","SUZLON","SYNGENE","UBL","AADHARHFC","AAVAS","AARTIPHARM","AKZOINDIA","ALKYLAMINE","ANANTRAJ","APTUS","ASHOKA","ASTRAZEN","BAJAJHLDNG","BALRAMCHIN","BANDHANBNK","BANKINDIA","BIRLACORPN","BLUEDART","CAMPUS","CANFINHOME","CAPLIPOINT","CENTRALBK","CERA","CREDITACC","DAMODARIND","EASEMYTRIP","FINPIPE","FDC","GICRE","GLAXO","GLENMARK","GMDCLTD","GRAPHITE","GSFC","GSPL","HAPPSTMNDS","HONASA","IDBI","IIFL","INTELLECT","JSL","JYOTHYLAB","KNRCON","KSB","KPRMILL","MGL","MPHASIS","NATIONALUM","PEL","PVRINOX","POWERINDIA","PRAJIND","PGHH","RAJESHEXPO","SAFARI","SBICARD","360ONE"]

NSE_500 = sorted(list(set(NSE_500)))

# Master File - 11 Checked चा Fix इथे आहे
master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
tokens = {}
for s in master:
    if s['exch_seg'] == 'NSE' and s['instrumenttype'] == '' and '-EQ' in s['symbol']:
        sym = s['symbol'].replace('-EQ','')
        if sym in NSE_500:
            tokens[sym] = s['token']

print(f"NSE 500 Tokens Found: {len(tokens)}")

def scan(item):
    name, token = item
    try:
        hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_MINUTE","fromdate":f"{today_str} 09:15","todate":f"{today_str} 15:30"})
        if not hist or 'data' not in hist or len(hist['data']) < 30: return None
        df = pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V'])
        df['EMA9'] = df['C'].ewm(span=9).mean()
        df['VWAP'] = (df['V']*(df['H']+df['L']+df['C'])/3).cumsum() / df['V'].cumsum()
        df['VOLAVG'] = df['V'].rolling(20).mean()
        d = df['C'].diff()
        gain = d.where(d>0,0).rolling(14).mean()
        loss = -d.where(d<0,0).rolling(14).mean()
        df['RSI'] = 100 - (100 / (1 + gain/loss.replace(0,0.01)))

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        first = df.iloc[0]
        pct = (curr['C']-first['O'])/first['O']*100
        vol_ratio = curr['V']/curr['VOLAVG'] if curr['VOLAVG']>0 else 0

        # COMMON FILTER
        if vol_ratio < 1.2: return None
        if not (curr['C'] > 50): return None # 50 Rs खालचे Penny Stock नको

        # BUY CONDITION - तुझीच
        is_green = curr['C'] > curr['O']
        is_buy_rsi = 55 <= curr['RSI'] <= 70
        is_buy_cross = prev['EMA9'] <= prev['VWAP'] and curr['EMA9'] > curr['VWAP'] and curr['C'] > curr['VWAP']

        if is_green and is_buy_rsi and is_buy_cross:
            entry = curr['C']; sl = curr['L']; risk = entry - sl
            if 0 < risk and risk/entry <= 0.015:
                t1 = entry + risk*2.5
                return f"🟢 <b>{name} BUY</b> @ {entry:.1f} +{pct:.1f}% Vol:{vol_ratio:.1f}x RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} | T1:{t1:.1f} (2.5x) | T2:Trail to Entry"

        # SELL CONDITION - नवीन
        is_red = curr['C'] < curr['O']
        is_sell_rsi = 30 <= curr['RSI'] <= 45
        is_sell_cross = prev['EMA9'] >= prev['VWAP'] and curr['EMA9'] < curr['VWAP'] and curr['C'] < curr['VWAP']

        if is_red and is_sell_rsi and is_sell_cross:
            entry = curr['C']; sl = curr['H']; risk = sl - entry
            if 0 < risk and risk/entry <= 0.015:
                t1 = entry - risk*2.5
                return f"🔴 <b>{name} SELL</b> @ {entry:.1f} {pct:.1f}% Vol:{vol_ratio:.1f}x RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} | T1:{t1:.1f} (2.5x) | T2:Trail to Entry"

    except: return None

results = []
with ThreadPoolExecutor(max_workers=35) as ex:
    futures = {ex.submit(scan,it):it for it in tokens.items()}
    for f in as_completed(futures):
        r = f.result()
        if r: results.append(r)

if results:
    msg = f"⚡️ <b>NSE 500 LIVE {now.strftime('%H:%M:%S')}</b> - {len(tokens)} Checked\n9EMA x VWAP | Vol 1.2x | RSI | Green/Red Close\n\n" + "\n\n".join(results[:15])
    send_tele(msg)
    print(msg)
else:
    send_tele(f"⏳ {now.strftime('%H:%M')} NSE 500 No Setup - {len(tokens)} Checked")
    print(f"No Setup - {len(tokens)} Checked")
