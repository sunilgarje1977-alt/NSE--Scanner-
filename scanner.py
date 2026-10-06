import os, requests, pandas as pd, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
totp = pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET").strip().replace(" ","").upper()).now()
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
    except: pass

# ===== SMALL CAP 400 FINAL LIST =====
STOCKS_5X = [
"360ONE","AADHARHFC","AAVAS","ABSLAMC","AEGISLOG","AFFLE","AARTIIND","ABFRL","ADANIGREEN","ADANIPOWER",
"AJANTPHARM","AKZOINDIA","ALEMBICLTD","ALKYLAMINE","AMBER","ANANDRATHI","ANGELONE","ANURAS","APARINDS","APLAPOLLO",
"APLLTD","APTUS","ARCHEAN","ASAHIINDIA","ASTERDM","ASTRAL","ATUL","AUBANK","AVANTIFEED","AVANTEL",
"BALAMINES","BALKRISIND","BALRAMCHIN","BANDHANBNK","BANKINDIA","BATAINDIA","BAYERCROP","BDL","BEML","BHEL",
"BIKAJI","BIOCON","BIRLACORPN","BLUEDART","BLUESTARCO","BSE","CAMS","CAMPUS","CAPLIPOINT","CARBORUNIV",
"CARTRADE","CASTROLIND","CCL","CEAT","CENTRALBK","CERA","CESC","CGCL","CHALET","CHAMBLFERT","CHEMPLASTS",
"CHENNPETRO","CHOICEIN","CHOLAFIN","CLEAN","COCHINSHIP","COFORGE","CRAFTSMAN","CREDITACC","CROMPTON","CSBBANK",
"CUB","CUPID","CYIENT","DATAPATTNS","DBCORP","DCBBANK","DEEPAKFERT","DEEPAKNTR","DELTACORP","DEVYANI",
"EASEMYTRIP","EDELWEISS","EICHERMOT","ELECON","ELGIEQUIP","EMBASSYDEV","ENDURANCE","EQUITASBNK","ERIS","EXIDEIND",
"FDC","FEDERALBNK","FINEORG","FSL","GABRIEL","GARFIBRES","GESHIP","GHCL","GLENMARK","GMRINFRA","GNFC","GODREJPROP",
"GRANULES","GRAPHITE","GRINDWELL","GRSE","GSFC","GSPL","GULFOILLUB","HAPPSTMNDS","HFCL","HINDCOPPER","HOMEFIRST",
"HONASA","HUDCO","IEX","IDBI","IDFCFIRSTB","IIFL","INDIACEM","INDIAMART","INDIANB","INDIGO","INDOCO","INDUSINDBK",
"INTELLECT","IOB","IPCALAB","IRCON","IRFC","JBCHEPHARM","JINDALSTEL","JUBLINGREA","JUBLFOOD","JUSTDIAL",
"JYOTHYLAB","KAJARIACER","KALYANKJIL","KARURVYSYA","KEC","KEI","KFINTECH","KPITTECH","KRBL","KPRMILL","KIMS",
"LATENTVIEW","LAURUSLABS","LEMONTREE","LTF","MANAPPURAM","MANYAVAR","MASTEK","MAXHEALTH","MCX","MEDANTA",
"METROPOLIS","MFSL","MOTHERSON","MOIL","MRPL","MUTHOOTFIN","NAM-INDIA","NATIONALUM","NAUKRI","NBCC","NCC",
"NH","NHPC","NMDC","NOCIL","NUVAMA","OBEROIRLTY","OLECTRA","ONWARDTEC","PEL","PERSISTENT","PETRONET","PFIZER",
"PHOENIXLTD","PNBHOUSING","PNCINFRA","POLYCAB","POLYMED","PRAJIND","PRESTIGE","PVRINOX","QUESS","RADICO","RAIN",
"RAILTEL","RALLIS","RBLBANK","REDINGTON","RITES","ROUTE","RVNL","SAIL","SAPPHIRE","SBICARD","SBFC","SOBHA",
"SONACOMS","SOUTHBANK","STLTECH","SUZLON","SYNGENE","TATACHEM","TATACOMM","TEJASNET","THOMASCOOK","TITAGARH",
"TRIDENT","TVSMOTOR","UJJIVANSFB","UNOMINDA","VOLTAS","WELCORP","YESBANK","ZEEL","ZENSARTECH","ZYDUSLIFE",
"BLS","DELHIVERY","DMART","FIVESTAR","GLAND","GRINFRA","LICHSGFIN","METROBRAND","NAZARA","NYKAA","POONAWALLA",
"TATATECH","UTIAMC","VIJAYA","ZOMATO","SUZLON","TRIDENT","YESBANK","CUPID","FSL","NUVAMA","DATAPATTNS","ELECON",
"GNFC","GODREJPROP","HFCL","IEX","IDFCFIRSTB","IRCON","IRFC","KARURVYSYA","KFINTECH","LEMONTREE","LTF","MANAPPURAM",
"MCX","MRPL","MUTHOOTFIN","NBCC","NHPC","OBEROIRLTY","PEL","PETRONET","PNBHOUSING","POLYCAB","PVRINOX","RBLBANK",
"RITES","RVNL","SAIL","SBICARD","SONACOMS","SOUTHBANK","TATACHEM","TITAGARH","UJJIVANSFB","UNOMINDA","VOLTAS",
"WELCORP","ZEEL","CEAT","FEDERALBNK","JINDALSTEL","JUSTDIAL","KAJARIACER","KALYANKJIL","MASTEK","RAIN","CHAMBLFERT",
"CHENNPETRO","CRAFTSMAN","CYIENT","DELTACORP","EQUITASBNK","HINDCOPPER","NATIONALUM","PERSISTENT","PNCINFRA","RADICO",
"RAILTEL","RALLIS","REDINGTON","ROUTE","SAPPHIRE","SBFC","SOBHA","STLTECH","SYNGENE","TATACOMM","TEJASNET","THOMASCOOK",
"TVSMOTOR","ZENSARTECH","ZYDUSLIFE","BLS","CLEAN","FINEORG","GLENMARK","GRANULES","HAPPSTMNDS","HOMEFIRST","HONASA",
"INDIAMART","KPRMILL","LAURUSLABS","MANYAVAR","MAXHEALTH","MEDANTA","METROPOLIS","MFSL","MOTHERSON","NATIONALUM",
"NAUKRI","NCC","NH","NMDC","PHOENIXLTD","POLYMED","PRAJIND","PRESTIGE","QUESS","CAMS","CAMPUS","CAPLIPOINT","CERA",
"CESC","CGCL","CHALET","CHEMPLASTS","CHOICEIN","CHOLAFIN","CLEAN","COCHINSHIP","COFORGE","CREDITACC","CROMPTON","CSBBANK"
]

def check(sym):
    token = token_map.get(sym)
    if not token: return None
    try:
        params = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        data = obj.getCandleData(params)
        if not data.get('data') or len(data['data']) < 30: return None
        df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema15'] = df['c'].ewm(span=15).mean()
        df['vwap'] = (df['c']*df['v']).cumsum()/df['v'].cumsum()
        df['vol20'] = df['v'].rolling(20).mean()
        df = df.tail(75)
        last = df.iloc[-1]; prev = df.iloc[-2]
        if last['c'] < 50: return None
        if last['v'] < 20000: return None
        if last['vol20']==0 or last['v'] < last['vol20']*1.8: return None
        if abs(last['c']-last['vwap'])/last['vwap'] > 0.025: return None
        volx = round(last['v']/last['vol20'],1)
        if prev['ema9'] < prev['ema15'] and last['ema9'] > last['ema15'] and last['c'] > last['vwap']:
            return {'sym': sym, 'side': "LONG", 'entry': last['c'], 'vwap': last['vwap'], 'volx': volx}
        if prev['ema9'] > prev['ema15'] and last['ema9'] < last['ema15'] and last['c'] < last['vwap']:
            return {'sym': sym, 'side': "SHORT", 'entry': last['c'], 'vwap': last['vwap'], 'volx': volx}
        return None
    except: return None

results = []
with ThreadPoolExecutor(max_workers=15) as exe:
    futures = {exe.submit(check, s): s for s in STOCKS_5X}
    for f in as_completed(futures):
        r = f.result()
        if r: results.append(r)

now_ist = datetime.now() + timedelta(hours=5, minutes=30)
time_str = now_ist.strftime("%H:%M")

if results:
    for trade in results[:5]:
        sl = round(trade['vwap']*0.997,2) if trade['side']=="LONG" else round(trade['vwap']*1.003,2)
        send_telegram(f"OK {trade['sym']} {trade['side']} @ {trade['entry']} VWAP {round(trade['vwap'],2)} SL {sl} Vol {trade['volx']}x {time_str}")
else:
    send_telegram(f"{time_str} - NO TRADE ({len(STOCKS_5X)}) Checked >50Rs Vol>20k Volx>1.8x") 
