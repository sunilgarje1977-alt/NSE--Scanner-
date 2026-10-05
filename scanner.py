import os, requests, pandas as pd, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Angel Login
obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

# Token Map
master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

# 5X MARGIN SMALLCAP LIST - 2.5x VOL
STOCKS_5X = ["BANDHANBNK","WELCORP","GROWW","DMART","ZENSAR","MRPL","IDEA","SUZLON","AEGISLOG","CDSL","CEATLTD","CAMS","CHALET","DEEPAKNTR","DELHIVERY","EQUITASBNK","GSPL","IEX","IRB","JUBLPHARMA","KEI","KARURVYSYA","LATENTVIEW","MAPMYINDIA","MEDPLUS","METROPOLIS","NAZARA","NYKAA","POLYMED","PRAJIND","RBA","ROUTE","SAPPHIRE","STLTECH","TANLA","TRIDENT","UJJIVANSFB","ZENTEC","BLS","CRAFTSMAN","FIVESTAR","HAPPSTMNDS","ANANDRATHI","AFFLE","ABSLAMC","APTUS","VIJAYA","STARHEALTH","KIMS","TIMKEN","SYNGENE","PVRINOX","RADICO","NATCOPHARM","BLUESTARCO","CLEAN","FINEORG","GALAXYSURF","ATUL","AARTIPHARM","JBCHEPHARM"]

def make_signal(sym, entry, side, vwap, volx):
    sl = round(vwap*0.997,2) if side=="LONG" else round(vwap*1.003,2)
    if side=="LONG":
        t1 = round(entry*1.01,2)
        t2 = round(entry*1.02,2)
        return f"✅ {sym} LONG @ {entry} | {volx}x VOL | 5x MARGIN\n SL: {sl} | VWAP\n T1: {t1} (1% 50% BOOK)\n T2: {t2} (2% TRAIL)\n 3:15 PM BOOK"
    else:
        t1 = round(entry*0.99,2)
        t2 = round(entry*0.98,2)
        return f"🔴 {sym} SHORT @ {entry} | {volx}x VOL | 5x MARGIN\n SL: {sl} | VWAP\n T1: {t1} (1% 50% BOOK)\n T2: {t2} (2% TRAIL)\n 3:15 PM BOOK"

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
        if last['v'] < last['vol20']*2.5: return None
        if abs(last['c']/last['vwap']-1) > 0.025: return None
        
        fresh_long = prev['ema9']<prev['vwap'] and last['ema9']>last['vwap'] and last['ema9']>last['ema15']
        fresh_short = prev['ema9']>prev['vwap'] and last['ema9']<last['vwap'] and last['ema9']<last['ema15']
        
        volx = round(last['v']/last['vol20'],1)
        if fresh_long: return make_signal(sym, round(last['c'],2), "LONG", last['vwap'], volx)
        if fresh_short: return make_signal(sym, round(last['c'],2), "SHORT", last['vwap'], volx)
    except: 
        return None

results=[]
with ThreadPoolExecutor(max_workers=20) as exe:
    futs = {exe.submit(check, s): s for s in STOCKS_5X}
    for f in as_completed(futs):
        r=f.result()
        if r: results.append(r)

now_ist = datetime.now() + timedelta(hours=5, minutes=30)

if now_ist.hour==15 and now_ist.minute>=10:
    msg = "⚠️ 3:15 PM SQUARE OFF ALERT ⚠️\nसगळे MIS 5x Position BOOK करा! ✅"
else:
    if results:
        msg = f"V51 SMALLCAP 5x 2.5xVOL {now_ist.strftime('%H:%M')} - {len(results[:7])} Signals:\n\n" + "\n\n".join(results[:7])
    else:
        msg = f"V51 {now_ist.strftime('%H:%M')} - NO TRADE (2.5x Vol नाही)"

requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", data={"chat_id":os.getenv('TELEGRAM_CHAT_ID'),"text":msg})
print(msg) 
