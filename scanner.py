import os, requests, pandas as pd, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Angel Login - NSE ONLY
obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now())

# NSE Token Map
master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace('-EQ',''): d['token'] for d in master if d.get('exch_seg')=='NSE' and str(d.get('symbol','')).endswith('-EQ')}

# 5x Margin Smallcap List
STOCKS_5X = ["BANDHANBNK","WELCORP","GROWW","DMART","ZENSAR","MRPL","IDEA","SUZLON","AEGISLOG","CDSL","CEATLTD","CAMS","CHALET","DEEPAKNTR","DELHIVERY","EQUITASBNK","GSPL","IEX","IRB","JUBLPHARMA","KEI","KARURVYSYA","LATENTVIEW","MAPMYINDIA","MEDPLUS","METROPOLIS","NAZARA","NYKAA","POLYMED","PRAJIND","RBA","ROUTE","SAPPHIRE","STLTECH","TANLA","TRIDENT","UJJIVANSFB","ZENTEC","BLS","CRAFTSMAN","FIVESTAR","HAPPSTMNDS","ANANDRATHI","AFFLE","ABSLAMC","APTUS","VIJAYA","STARHEALTH","KIMS","TIMKEN","SYNGENE","PVRINOX","RADICO","NATCOPHARM","BLUESTARCO","CLEAN","FINEORG","GALAXYSURF","ATUL","AARTIPHARM","JBCHEPHARM","CROMPTON","ITC","ASHOKLEY","BALKRISIND","BATAINDIA","BHEL","CANBK","FEDERALBNK","SAIL","TATAPOWER","ZEEL"]

def make_signal(sym, entry, side, vwap, volx):
    if side == "LONG":
        sl = round(vwap*0.997, 2)
        t1 = round(entry*1.01, 2)
        t2 = round(entry*1.02, 2)
        return f"✅ {sym} LONG @ {entry} | {volx}x VOL | 5x\nSL: {sl} | T1 {t1} T2 {t2}"
    else:
        sl = round(vwap*1.003, 2)
        t1 = round(entry*0.99, 2)
        t2 = round(entry*0.98, 2)
        return f"🔴 {sym} SHORT @ {entry} | {volx}x VOL | 5x\nSL: {sl} | T1 {t1} T2 {t2}"

def check(sym):
    token = token_map.get(sym)
    if not token: return None
    try:
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIVE_MINUTE",
            "fromdate": (datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
            "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
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
        if last['c'] < 50 or last['c'] > 3000: return None
        if last['vol20'] == 0: return None
        if last['v'] > 0 and last['v'] < last['vol20']*1.8: return None
        if abs(last['c']/last['vwap']-1) > 0.025: return None
        volx = round(last['v']/last['vol20'],1)
        # BUY - CROMPTON/ITC Type
        if prev['ema9'] < prev['ema15'] and last['ema9'] > last['ema15'] and last['c'] > last['vwap']:
            return make_signal(sym, last['c'], "LONG", last['vwap'], volx)
        # SELL - BANDHANBNK Type
        if prev['ema9'] > prev['ema15'] and last['ema9'] < last['ema15'] and last['c'] < last['vwap']:
            return make_signal(sym, last['c'], "SHORT", last['vwap'], volx)
    except:
        return None

results = []
with ThreadPoolExecutor(max_workers=40) as exe:
    futures = {exe.submit(check, s): s for s in STOCKS_5X}
    for f in as_completed(futures):
        r = f.result()
        if r: results.append(r)

now_ist = datetime.now() + timedelta(hours=5, minutes=30)
time_str = now_ist.strftime('%H:%M')

if results:
    msg = f"🚀 ANGEL NSE {time_str} - {len(results)} Signals\n\n" + "\n\n".join(results[:10])
else:
    msg = f"⏰ ANGEL NSE {time_str} - NO TRADE\n{len(STOCKS_5X)} Stocks Checked (NSE)"

requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", data={"chat_id": os.getenv('TELEGRAM_CHAT_ID'), "text": msg})
print(msg)
