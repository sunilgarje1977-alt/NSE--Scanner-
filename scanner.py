import os, requests, pandas as pd, pyotp, time
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- SETUP ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

def send_telegram(msg):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})

# 50₹+ 5x STOCKS
STOCKS_5X = ["5PAISA","AARTIIND","AAVAS","ABSLAMC","AEGISLOG","AFFLE","AHLUCONT","ALKYLAMINE","AMBER","ANANDRATHI","ANANTRAJ","ANGELONE","APARINDS","APOLLOTYRE","APTUS","ARVIND","ASHOKLEY","ASTERDM","ATUL","AUBANK","AVANTIFEED","BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BEML","BERGEPAINT","BHEL","BIOCON","BLS","BLUESTARCO","BRIGADE","BSE","BSOFT","CAMS","CANBK","CAPLIPOINT","CARBORUNUM","CASTROLIND","CCL","CDSL","CEATLTD","CERA","CHALET","CHAMBLFERT","CLEAN","CMSINFO","COFORGE","CONCOR","CRAFTSMAN","CREDITACC","CRISIL","CROMPTON","CUB","CUMMINSIND","CYIENT","DABUR","DALBHARAT","DATAPATTNS","DEEPAKFERT","DEEPAKNTR","DELHIVERY","DELTACORP","DIVISLAB","DMART","EICHERMOT","EIDPARRY","EIHOTEL","ELGIEQUIP","EMAMILTD","ENDURANCE","EQUITASBNK","FEDERALBNK","FINEORG","FIVESTAR","FSL","GALAXYSURF","GODREJPROP","GRANULES","GRASIM","GSPL","HAL","HAPPSTMNDS","HINDCOPPER","HUDCO","IEX","INDHOTEL","INDIAMART","INTELLECT","IPCALAB","IRB","JINDALSTEL","JKCEMENT","JUBLFOOD","JUSTDIAL","KAJARIA","KARURVYSYA","KEI","KIMS","LATENTVIEW","LAURUSLABS","LEMONTREE","LTF","LTTS","LUPIN","MAPMYINDIA","MASTEK","MCX","MEDPLUS","METROPOLIS","MFSL","MGL","MOTHERSON","MPHASIS","MRPL","MUTHOOTFIN","NAM-INDIA","NATCOPHARM","NATIONALUM","NAUKRI","NAVINFLUOR","NBCC","NCC","NHPC","NMDC","OBEROIRL","OFSS","OIL","PAGEIND","PEL","PERSISTENT","PHOENIXLTD","PIDILITIND","PIIND","POLYCAB","POONAWALLA","PRAJIND","PRESTIGE","PVRINOX","RADICO","RBA","RBLBANK","RECLTD","ROUTE","SAIL","SAPPHIRE","SBICARD","SHREECEM","SJVN","SRF","SUNTV","TANLA","TATACHEM","TATACOMM","TATAPOWER","TIMKEN","TRIDENT","UJJIVANSFB","UBL","UPL","VEDL","VOLTAS","WELCORP","ZENSAR","ZENTEC","ZEEL","ZYDUSLIFE"]

# --- SCAN LOGIC ---
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
        if last['c'] < 50: return None # फक्त 50₹+ शेअर
        if last['vol20'] == 0 or last['v'] < last['vol20']*1.8: return None
        if abs(last['c']/last['vwap']-1) > 0.025: return None
        volx = round(last['v']/last['vol20'],1)
        if prev['ema9'] < prev['ema15'] and last['ema9'] > last['ema15'] and last['c'] > last['vwap']:
            return {"sym":sym, "side":"LONG", "entry":last['c'], "vwap":last['vwap'], "volx":volx}
        if prev['ema9'] > prev['ema15'] and last['ema9'] < last['ema15'] and last['c'] < last['vwap']:
            return {"sym":sym, "side":"SHORT", "entry":last['c'], "vwap":last['vwap'], "volx":volx}
    except: return None

# --- TRAILING BOT LOGIC ---
active_trades = {} # sym -> {entry, sl, side}

def start_trailing(trade):
    sym = trade['sym']
    entry = trade['entry']
    vwap = trade['vwap']
    side = trade['side']
    sl = round(vwap*0.997,2) if side=="LONG" else round(vwap*1.003,2)
    active_trades[sym] = {"entry":entry, "sl":sl, "side":side, "trail_stage":0}
    msg = f"✅ {sym} {side} @ {entry} | SL: {sl}\nTrail: >1% -> Cost | >2% -> 1% Lock"
    send_telegram(msg)
    print(msg)

def monitor_trailing():
    # हा Loop दर 1 मिनिटाला चालेल
    for sym, t in list(active_trades.items()):
        token = token_map.get(sym)
        try:
            params = {"exchange": "NSE","symboltoken": token,"interval": "ONE_MINUTE","fromdate": (datetime.now()-timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M"),"todate": datetime.now().strftime("%Y-%m-%d %H:%M")}
            data = obj.getCandleData(params)
            ltp = data['data'][-1][4]
            entry = t['entry']
            side = t['side']
            old_sl = t['sl']
            new_sl = old_sl

            if side == "LONG":
                profit_pct = (ltp - entry)/entry
                if profit_pct >= 0.02 and t['trail_stage'] < 2:
                    new_sl = round(entry*1.01,2)
                    t['trail_stage']=2
                elif profit_pct >= 0.01 and t['trail_stage'] < 1:
                    new_sl = entry
                    t['trail_stage']=1
                # SL HIT
                if ltp <= old_sl:
                    send_telegram(f"❌ EXIT {sym} LONG @ {ltp} | SL Hit | P/L: {round((ltp-entry)/entry*100,2)}%")
                    del active_trades[sym]
                    continue
            else: # SHORT
                profit_pct = (entry - ltp)/entry
                if profit_pct >= 0.02 and t['trail_stage'] < 2:
                    new_sl = round(entry*0.99,2)
                    t['trail_stage']=2
                elif profit_pct >= 0.01 and t['trail_stage'] < 1:
                    new_sl = entry
                    t['trail_stage']=1
                if ltp >= old_sl:
                    send_telegram(f"❌ EXIT {sym} SHORT @ {ltp} | SL Hit | P/L: {round((entry-ltp)/entry*100,2)}%")
                    del active_trades[sym]
                    continue

            if new_sl!= old_sl:
                t['sl'] = new_sl
                send_telegram(f"🔄 TRAIL UPDATE: {sym} @ {ltp}\nSL: {old_sl} -> {new_sl} ({'Cost' if t['trail_stage']==1 else '1% Lock'})")
        except: pass

# --- MAIN SCAN ---
results = []
with ThreadPoolExecutor(max_workers=15) as exe:
    futures = {exe.submit(check, s): s for s in STOCKS_5X}
    for f in as_completed(futures):
        r = f.result()
        if r: results.append(r)

now_ist = datetime.now() + timedelta(hours=5, minutes=30)
time_str = now_ist.strftime('%H:%M')

if results:
    for trade in results[:5]: # पहिले 5 Signal घे
        start_trailing(trade)
else:
    send_telegram(f"⏰ {time_str} - NO TRADE\n{len(STOCKS_5X)} Checked (5x >10₹)")

# Trailing Check (GitHub Action मध्ये 1 वेळा चालेल, VPS वर असेल तर Loop लाव)
monitor_trailing()
