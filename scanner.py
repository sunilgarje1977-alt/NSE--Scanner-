import os, requests, pandas as pd, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

STOCKS_5X = ["BANDHANBNK","WELCORP","GROWW","DMART","ZENSAR","MRPL","IDEA","SUZLON","AEGISLOG","CDSL","CEATLTD","CAMS","CHALET","DEEPAKNTR","DELHIVERY","EQUITASBNK","GSPL","IEX","IRB","JUBLPHARMA","KEI","KARURVYSYA","LATENTVIEW","MAPMYINDIA","MEDPLUS","METROPOLIS","NAZARA","NYKAA","POLYMED","PRAJIND","RBA","ROUTE","SAPPHIRE","STLTECH","TANLA","TRIDENT","UJJIVANSFB","ZENTEC","BLS","CRAFTSMAN","FIVESTAR","HAPPSTMNDS","ANANDRATHI","AFFLE","ABSLAMC","APTUS","VIJAYA","STARHEALTH","KIMS","TIMKEN","SYNGENE","PVRINOX","RADICO","NATCOPHARM","BLUESTARCO","CLEAN","FINEORG","GALAXYSURF","ATUL","AARTIPHARM","JBCHEPHARM"]

def make_signal(sym, entry, side, vwap, volx):
    sl = round(vwap*0.997,2) if side=="LONG" else round(vwap*1.003,2)
    t1 = round(entry*1.01,2) if side=="LONG" else round(entry*0.99,2)
    t2 = round(entry*1.02,2) if side=="LONG" else round(entry*0.98,2)
    if side=="LONG":
        return f"✅ {sym} LONG @ {entry} | {volx}x VOL\nSL: {sl} | T1 {t1} T2 {t2}"
    else:
        return f"🔴 {sym} SHORT @ {entry} | {volx}x VOL\nSL: {sl} | T1 {t1} T2 {t2}"

def check(sym):
    token = token_map.get(sym)
    if not token: return None
    try:
        p = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),"todate": datetime.now().strftime("%Y-%m-%d %H:%M")}
        d = obj.getCandleData(p)
        if not d['data']: return None
        df = pd.DataFrame(d['data'], columns=['ts','o','h','l','c','v'])
        df['ema9']=df['c'].ewm(span=9).mean()
        df['ema15']=df['c'].ewm(span=15).mean()
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
        df['vol20']=df['v'].rolling(20).mean()
        last=df.iloc[-1]; prev=df.iloc[-2]
        if last['c']<20 or last['c']>1500: return None
        if last['v'] < last['vol20']*2.0: return None
        if abs(last['c']/last['vwap']-1) > 0.025: return None
        volx = round(last['v']/last['vol20'],1)
        if prev['ema9']<prev['vwap'] and last['ema9']>last['vwap'] and last['ema9']>last['ema15']:
            return make_signal(sym, last['c'], "LONG", last['vwap'], volx)
        if prev['ema9']>prev['vwap'] and last['ema9']<last['vwap'] and last['ema9']<last['ema15']:
            return make_signal(sym, last['c'], "SHORT", last['vwap'], volx)
    except: return None

results=[]
with ThreadPoolExecutor(max_workers=30) as exe:
    for f in as_completed({exe.submit(check, s): s for s in STOCKS_5X}):
        r=f.result()
        if r: results.append(r)

now_ist = datetime.now() + timedelta(hours=5, minutes=30)
msg = f"ANGEL NSE {now_ist.strftime('%H:%M')} - {len(results)} Signals\n\n" + "\n\n".join(results[:10]) if results else f"ANGEL NSE {now_ist.strftime('%H:%M')} - NO TRADE"
requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", data={"chat_id":os.getenv('TELEGRAM_CHAT_ID'),"text":msg})
print(msg)
