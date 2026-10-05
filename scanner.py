import os, requests, pandas as pd, time, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta

# --- LOGIN - तुझ्या Secret मधून येतं ---
print("Logging to Angel...")
obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
totp = pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)

# --- 400 Smallcap Tokens - Auto Download ---
print("Downloading Angel Master...")
master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
token_map = {d['symbol'].replace("-EQ",""): d['token'] for d in master if d['exch_seg']=='NSE' and d['symboltype']=='EQ'}

# NSE 400 List
try:
    r = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
    df_nse = pd.read_csv(pd.io.common.StringIO(r.text))
    SYMBOLS = [s for s in df_nse['SYMBOL'].astype(str).str.strip() if "-" not in s][:400]
except:
    SYMBOLS = ["BANDHANBNK","WELCORP","DPWIRES","GROWW","DMART","PFOCUS","MRPL","ZENSAR","IDEA","SUZLON"]

print(f"Total {len(SYMBOLS)} to scan")

# --- तुझा V51 Rule + Volume Check ---
results = []
for sym in SYMBOLS:
    token = token_map.get(sym)
    if not token: continue
    try:
        param = {"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE",
                 "fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
                 "todate": datetime.now().strftime("%Y-%m-%d %H:%M")}
        data = obj.getCandleData(param)
        if not data['data']: continue
        df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        df['ema9']=df['c'].ewm(span=9).mean()
        df['ema15']=df['c'].ewm(span=15).mean()
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
        df['vol20']=df['v'].rolling(20).mean()
        last=df.iloc[-1]; prev=df.iloc[-2]

        # 1. DPWIRES Filter - Circuit
        if abs(last['c']/prev['c']-1) > 0.15: continue
        # 2. Volume Filter - तू सांगितलास
        if last['v'] < last['vol20']*1.5: continue

        long_c = last['ema9']>last['vwap'] and last['ema15']>last['vwap'] and last['ema9']>last['ema15'] and last['c']>last['vwap']
        short_c = last['ema9']<last['vwap'] and last['ema15']<last['vwap'] and last['ema9']<last['ema15'] and last['c']<last['vwap']
        
        if long_c: results.append(f"✅ {sym} LONG @ {last['c']}")
        elif short_c: results.append(f"🔴 {sym} SHORT @ {last['c']}")
    except: pass
    time.sleep(0.35) # Angel ला Speed Limit आहे

# Telegram ला पाठव
if results:
    msg = f"V51 Smallcap 400 - {len(results)} Signals:\n" + "\n".join(results)
    requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
                  data={"chat_id":os.getenv('TELEGRAM_CHAT_ID'),"text":msg})
    print(msg)
else:
    print("DONE - Cross नाही - NO TRADE")
