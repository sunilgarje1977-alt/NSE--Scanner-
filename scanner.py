import os, requests, pandas as pd, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

# --- 5X MARGIN Smallcap List - हे Angel MIS मध्ये 5x देतात ---
MARGIN_5X_SMALLCAP = [
"BANDHANBNK","WELCORP","GROWW","DMART","ZENSAR","MRPL","IDEA","SUZLON","AEGISLOG","CDSL","CEATLTD",
"CAMS","CHALET","DEEPAKNTR","DELHIVERY","EQUITASBNK","GSPL","IEX","IRB","JUBLPHARMA","KEI","KARURVYSYA",
"LATENTVIEW","MAPMYINDIA","MEDPLUS","METROPOLIS","NAZARA","NYKAA","POLYMED","PRAJIND","RBA","ROUTE",
"SAPPHIRE","STLTECH","TANLA","TRIDENT","UJJIVANSFB","ZENTEC","BLS","CRAFTSMAN","FIVESTAR","HAPPSTMNDS",
"ANANDRATHI","AFFLE","ABSLAMC","APTUS","VIJAYA","STARHEALTH","KIMS","TIMKEN","SYNGENE","PVRINOX",
"RADICO","NATCOPHARM","BLUESTARCO","CLEAN","FINEORG","GALAXYSURF","ATUL","AARTIPHARM","JBCHEPHARM",
"JKLAKSHMI","LEMONTREE","INDIACEM","HOMEFIRST","CHEMPLASTS","DEVYANI","BIKAJI","MUTHOOTMF","NUVAMA"
]

def make_signal(sym, entry, side, vwap, volx):
    sl = round(vwap*0.997,2) if side=="LONG" else round(vwap*1.003,2)
    return f"{'✅' if side=='LONG' else '🔴'} {sym} {side} @ {entry} | {volx}x VOL | 5x MARGIN\n SL: {sl}\n T1: {round(entry*1.01,2) if side=='LONG' else round(entry*0.99,2)} (1% 50% BOOK)\n T2: {round(entry*1.02,2) if side=='LONG' else round(entry*0.98,2)} (2% TRAIL)\n MIS 5x - 3:15 BOOK"

def check(sym):
    token = token_map.get(sym)
    if not token: return None
    try:
        p = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),"todate": datetime.now().strftime("%Y-%m-%d %H:%M")}
        d = obj.getCandleData(p)
        if not d['data']: return None
        df = pd.DataFrame(d['data'], columns=['ts','o','h','l','c','v'])
        df['ema9']=df['c'].ewm(span=9).mean(); df['ema15']=df['c'].ewm(span=15).mean()
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum(); df['vol20']=df['v'].rolling(20).mean()
        last=df.iloc[-1]; prev=df.iloc[-2]
        if last['c']<20 or last['c']>1500: return None
        if last['v'] < last['vol20']*2.5: return None # Volume Filter
        fresh_long = prev['ema9']<prev['vwap'] and last['ema9']>last['vwap']
        fresh_short = prev['ema9']>prev['vwap'] and last['ema9']<last['vwap']
        volx = int(last['v']/last['vol20'])
        if fresh_long: return make_signal(sym, round(last['c'],2), "LONG", last['vwap'], volx)
        if fresh_short: return make_signal(sym, round(last['c'],2), "SHORT", last['vwap'], volx)
    except: return None

results=[]
with ThreadPoolExecutor(max_workers=20) as exe:
    for f in as_completed({exe.submit(check, s): s for s in MARGIN_5X_SMALLCAP}):
        r=f.result()
        if r: results.append(r)

results = sorted(results, key=lambda x: 0, reverse=True)[:7]
now_ist = datetime.now() + timedelta(hours=5, minutes=30)
msg = f"V51 SMALLCAP 5x MARGIN {now_ist.strftime('%H:%M')} - {len(results)} Signals:\n\n" + "\n\n".join(results) if results else f"V51 5x {now_ist.strftime('%H:%M')} - NO TRADE"

# 3:15 Square off
if now_ist.hour==15 and now_ist.minute>=10:
    msg = "⚠️ 3:15 PM SQUARE OFF - MIS 5x वाले सगळे BOOK करा! ✅"

requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", data={"chat_id":os.getenv('TELEGRAM_CHAT_ID'),"text":msg})
print(msg)
