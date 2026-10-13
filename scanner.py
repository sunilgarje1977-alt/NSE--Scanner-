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
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"HTML"}, timeout=20)
    except: pass

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist)
today_str=now.strftime("%Y-%m-%d")

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

NSE_500 = ["360ONE","3MINDIA","ABB","ACC","AARTIIND","ADANIENT","ADANIGREEN","ADANIPOWER","ADANIPORTS","AFFLE","AJANTPHARM","ALKEM","AMBUJACEM","ANANDRATHI","ANGELONE","APOLLOHOSP","APOLLOTYRE","ASHOKLEY","ASIANPAINT","ASTERDM","ASTRAL","ATGL","AUBANK","AUROPHARMA","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BALKRISIND","BANKBARODA","BATAINDIA","BDL","BEL","BEML","BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BPCL","BRITANNIA","BSE","BSOFT","CAMS","CANBK","CDSL","CESC","CGPOWER","CHOLAFIN","CIPLA","COALINDIA","COCHINSHIP","COFORGE","COLPAL","CONCOR","CROMPTON","CUB","CUMMINSIND","CYIENT","DABUR","DALBHARAT","DEEPAKNTR","DELHIVERY","DIVISLAB","DIXON","DLF","DMART","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","FSL","GAIL","GICRE","GLAND","GODREJCP","GODREJPROP","GRANULES","GRASIM","GRSE","HAL","HDFCBANK","HDFCLIFE","HAVELLS","HEROMOTOCO","HINDALCO","HINDUNILVR","HINDZINC","HUDCO","ICICIBANK","ICICIGI","ICICIPRULI","IEX","IDEA","IDFCFIRSTB","INDHOTEL","INDIAMART","INDIGO","INDUSINDBK","INDUSTOWER","INFY","INOXWIND","INTELLECT","IOC","IPCALAB","IRB","IRCTC","IRFC","IREDA","ITC","JINDALSTEL","JIOFIN","JKCEMENT","JSWENERGY","JSWSTEEL","JUBLFOOD","KAJARIACER","KALYANKJIL","KEI","KFINTECH","KPITTECH","KPRMILL","LTF","LT","LTIM","LTTS","LICI","LUPIN","M&M","M&MFIN","MANAPPURAM","MARICO","MARUTI","MAZDOCK","MCX","MGL","MOTHERSON","MPHASIS","MRF","MUTHOOTFIN","NATIONALUM","NAUKRI","NBCC","NCC","NESTLEIND","NHPC","NMDC","NTPC","OBEROIRLTY","OIL","ONGC","PAGEIND","PAYTM","PERSISTENT","PETRONET","PFC","PIDILITIND","PNB","POLYCAB","POWERGRID","PRESTIGE","PVRINOX","RECLTD","RELIANCE","RVNL","SAIL","SBIN","SBICARD","SBILIFE","SRF","SUNPHARMA","TATACOMM","TATACONSUM","TATAPOWER","TATASTEEL","TATAMOTORS","TCS","TECHM","TITAN","TORNTPHARM","TORNTPOWER","TRENT","TVSMOTOR","ULTRACEMCO","UPL","VEDL","VBL","VOLTAS","WIPRO","ZOMATO","ZYDUSLIFE","ABBOTINDIA","AARTIPHARM","AEGISLOG","ALEMBICLTD","AMBER","APARINDS","ASAHIINDIA","ATUL","AVANTIFEED","BAYERCROP","BBTC","BERGEPAINT","BLUESTARCO","CARBORUN","CASTROLIND","CENTURYPLY","CHALET","CHAMBLFERT","CRISIL","CSBBANK","DATAPATTNS","DEVYANI","EIDPARRY","EIHOTEL","ELGIEQUIP","ENDURANCE","FINEORG","FINCABLES","GALAXYSURF","GILLETTE","GLAXO","GLENMARK","GMDCLTD","GODFRYPHLP","GPPL","GRAPHITE","GRINFRA","GSFC","GSPL","HAPPSTMNDS","HDFCAMC","HONASA","INDIACEM","INDIANB","JKTYRE","JMFINANCIL","JSL","JUSTDIAL","KARURVYSYA","KSB","LAURUSLABS","LICHSGFIN","LINDEINDIA","METROBRAND","NATCOPHARM","PATANJALI","PEL","PNBHOUSING","POLYMED","POONAWALLA","RADICO","RAILTEL","RBLBANK","RELAXO","SAFARI","SBI","SJVN","SKFINDIA","SUNTV","SUPREMEIND","SUZLON","SYNGENE","UBL","AADHARHFC","AAVAS","ADANIENSOL","ADVENZYMES","AKZOINDIA","ALIVUS","ALKYLAMINE","ALOKINDS","ANANTRAJ","APTUS","ARCHEAN","ASHOKA","ASTRAZEN","ATUL","BAGFIN","BAJAJHFL","BALRAMCHIN","BANDHANBNK","BANKINDIA","BEPL","BIRLACORPN","BLUEDART","BONLON","BSOFT","CAMPUS","CANFINHOME","CAPLIPOINT","CENTRALBK","CERA","CHAMBLFERT","CREDITACC","CUMMINSIND","DAMODARIND","DEEPAKFERT","DYNAMIND","EASEMYTRIP","EIDPARRY","FINPIPE","FDC","GIC","IDBI","IIFLFIN","IPCALAB","JBCHEPHARM","JKLAKSHMI","JKPAPER","JYOTHYLAB","KNRCON","KPIL","KARURVYSYA"]

master=requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=20).json()
tokens={}
for s in master:
    if s['exch_seg']=='NSE' and s['symbol'].replace('-EQ','') in NSE_500 and s['instrumenttype']=='':
        sym=s['symbol'].replace('-EQ','')
        if sym not in tokens: tokens[sym]=s['token']

def scan(item):
    name, token=item
    try:
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_MINUTE","fromdate":f"{today_str} 09:15","todate":f"{today_str} 15:30"})
        if not hist or 'data' not in hist or len(hist['data'])<25: return None
        df=pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V'])
        df['EMA9']=df['C'].ewm(span=9).mean()
        df['VWAP']=(df['V']*(df['H']+df['L']+df['C'])/3).cumsum()/df['V'].cumsum()
        df['VOLAVG']=df['V'].rolling(20).mean()
        d=df['C'].diff()
        df['RSI']=100-(100/(1+d.where(d>0,0).rolling(9).mean()/-d.where(d<0,0).rolling(9).mean().replace(0,0.01)))
        curr=df.iloc[-1]; prev=df.iloc[-2]; first=df.iloc[0]
        pct=(curr['C']-first['O'])/first['O']*100
        vol_ratio=curr['V']/curr['VOLAVG'] if curr['VOLAVG']>0 else 1

        # BUY
        is_green = curr['C'] > curr['O']
        is_buy_vol = vol_ratio >= 1.2
        is_buy_rsi = 55 <= curr['RSI'] <= 70
        is_buy_cross = prev['EMA9'] <= prev['VWAP'] and curr['EMA9'] > curr['VWAP']

        if is_green and is_buy_vol and is_buy_rsi and is_buy_cross and curr['C']>curr['VWAP']:
            entry=curr['C']; sl=curr['L']; risk=entry-sl
            if risk>0 and risk/entry<=0.02:
                t1=entry+risk*2.5
                return f"🟢 <b>{name} BUY</b> @ {entry:.1f} +{pct:.1f}% Vol:{vol_ratio:.1f}x RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} T1:{t1:.1f} (2.5x) T2:Trail"

        # SELL
        is_red = curr['C'] < curr['O']
        is_sell_vol = vol_ratio >= 1.2
        is_sell_rsi = 30 <= curr['RSI'] <= 45
        is_sell_cross = prev['EMA9'] >= prev['VWAP'] and curr['EMA9'] < curr['VWAP']

        if is_red and is_sell_vol and is_sell_rsi and is_sell_cross and curr['C']<curr['VWAP']:
            entry=curr['C']; sl=curr['H']; risk=sl-entry
            if risk>0 and risk/entry<=0.02:
                t1=entry-risk*2.5
                return f"🔴 <b>{name} SELL</b> @ {entry:.1f} {pct:.1f}% Vol:{vol_ratio:.1f}x RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} T1:{t1:.1f} (2.5x) T2:Trail"

    except: return None

results=[]
with ThreadPoolExecutor(max_workers=30) as ex:
    for f in as_completed({ex.submit(scan,it):it for it in tokens.items()}):
        r=f.result()
        if r: results.append(r)

if results:
    msg=f"⚡️ <b>NSE 500 BUY/SELL {now.strftime('%H:%M:%S')}</b> {len(tokens)} Checked\n\n" + "\n\n".join(results[:15])
    send_tele(msg)
else:
    send_tele(f"⏳ {now.strftime('%H:%M')} NSE 500 No Setup - {len(tokens)} Checked") 
