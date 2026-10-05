import os, requests, pandas as pd, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

def send_telegram(msg):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=10)

STOCKS_5X = ["AARTIIND","AAVAS","ABSLAMC","AEGISLOG","AFFLE","AHLUCONT","ALKYLAMINE","AMBER","ANANDRATHI","ANANTRAJ","ANGELONE","APARINDS","APOLLOTYRE","APTUS","ARVIND","ASHOKLEY","ASTERDM","ATUL","AUBANK","AVANTIFEED","BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BEML","BERGEPAINT","BHEL","BIOCON","BLS","BLUESTARCO","BRIGADE","BSE","BSOFT","CAMS","CANBK","CAPLIPOINT","CARBORUNUM","CASTROLIND","CCL","CDSL","CEATLTD","CERA","CHALET","CHAMBLFERT","CLEAN","CMSINFO","COFORGE","CONCOR","CRAFTSMAN","CREDITACC","CRISIL","CROMPTON","CUB","CUMMINSIND","CYIENT","DABUR","DALBHARAT","DATAPATTNS","DEEPAKFERT","DEEPAKNTR","DELHIVERY","DELTACORP","DIVISLAB","DMART","EICHERMOT","EIDPARRY","EIHOTEL","ELGIEQUIP","EMAMILTD","ENDURANCE","EQUITASBNK","FEDERALBNK","FINEORG","FIVESTAR","FSL","GALAXYSURF","GODREJPROP","GRANULES","GRASIM","GSPL","HAL","HAPPSTMNDS","HINDCOPPER","HUDCO","IEX","INDHOTEL","INDIAMART","INTELLECT","IPCALAB","IRB","JINDALSTEL","JKCEMENT","JUBLFOOD","JUSTDIAL","KAJARIA","KARURVYSYA","KEI","KIMS","LATENTVIEW","LAURUSLABS","LEMONTREE","LTF","LTTS","LUPIN","MAPMYINDIA","MASTEK","MCX","MEDPLUS","METROPOLIS","MFSL","MGL","MOTHERSON","MPHASIS","MRPL","MUTHOOTFIN","NAM-INDIA","NATCOPHARM","NATIONALUM","NAUKRI","NAVINFLUOR","NBCC","NCC","NHPC","NMDC","OBEROIRL","OFSS","OIL","PAGEIND","PEL","PERSISTENT","PHOENIXLTD","PIDILITIND","PIIND","POLYCAB","POONAWALLA","PRAJIND","PRESTIGE","PVRINOX","RADICO","RBA","RBLBANK","RECLTD","ROUTE","SAIL","SAPPHIRE","SBICARD","SHREECEM","SJVN","SRF","SUNTV","TANLA","TATACHEM","TATACOMM","TATAPOWER","TIMKEN","TRIDENT","UJJIVANSFB","UBL","UPL","VEDL","VOLTAS","WELCORP","ZENSAR","ZENTEC","ZEEL","ZYDUSLIFE"]

def check(sym):
    token = token_map.get(sym)
    if not token: return None
    try:
        params = {"exchange": "NSE","symboltoken": token,"interval": "FIVE_MINUTE","fromdate": (datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),"todate": datetime.now().strftime("%Y-%m-%d %H:%M")}
        data = obj.getCandleData(params)
        if not data.get('data') or len(data['data']) < 30: return None
        df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        df = df.tail(75)
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema15'] = df['c'].ewm(span=15).mean()
        df['vwap'] = (df['c']*df['v']).cumsum()/df['v'].cumsum()
        df['vol20'] = df['v'].rolling(20).mean()
        last = df.iloc[-1]
        prev = df.iloc[-2]
        if last['c'] < 50: return None
        if last['v'] < 20000: return None
        if last['vol20'] == 0 or last['v'] < last['vol20']*1.8: return None
        if abs(last['c']/last['vwap']-1) > 0.025: return None
        volx = round(last['v']/last['vol20'],1)
        if prev['ema9'] < prev['ema15'] and last['ema9'] > last['ema15'] and last['c'] > last['vwap']:
            return {"sym":sym, "side":"LONG", "entry":last['c'], "vwap":last['vwap'], "volx":volx}
        if prev['ema9'] > prev['ema15'] and last['ema9'] < last['ema15'] and last['c'] < last['vwap']:
            return {"sym":sym, "side":"SHORT", "entry":last['c'], "vwap":last['vwap'], "volx":volx}
    except: return None

results = []
with ThreadPoolExecutor(max_workers=15) as exe:
    futures = {exe.submit(check, s): s for s in STOCKS_5X}
    for f in as_completed(futures):
        r = f.result()
        if r: results.append(r)

now_ist = datetime.now() + timedelta(hours=5, minutes=30)
time_str = now_ist.strftime('%H:%M')

if results:
    for trade in results[:5]:
        sl = round(trade['vwap']*0.997,2) if trade['side']=="LONG" else round(trade['vwap']*1.003,2)
        send_telegram(f"OK {trade['sym']} {trade['side']} @ {trade['entry']} SL:{sl} Vol:{trade['volx']}x")
else:
    send_telegram(f"{time_str} - NO TRADE {len(STOCKS_5X)} Checked >50Rs 20kVol")
