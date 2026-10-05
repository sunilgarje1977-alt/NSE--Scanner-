import os, requests, pandas as pd, time, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta

print("Starting V51 Scanner...")

# --- 1. Angel Login ---
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD") # इथे 4 अंकी MPIN हवा!
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

obj = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
session = obj.generateSession(CLIENT_ID, PASSWORD, totp)
print(f"Angel Login: {session}")

# --- 2. Token Map Auto - Fix केलेला ---
print("Downloading Token Map...")
url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
master = requests.get(url, timeout=30).json()
# Fix: symboltype नाही - फक्त -EQ बघतोय
token_map = {}
for d in master:
    if d.get('exch_seg') == 'NSE' and str(d.get('symbol','')).endswith('-EQ'):
        sym = d['symbol'].replace('-EQ','').strip()
        token_map[sym] = d['token']

print(f"Tokens Loaded: {len(token_map)}")

# --- 3. NSE 400 List ---
def get_symbols():
    try:
        r = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv",
                         headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
        df = pd.read_csv(pd.io.common.StringIO(r.text))
        syms = [s.strip() for s in df['SYMBOL'].tolist() if "-" not in str(s)]
        return syms[:400]
    except:
        return ["BANDHANBNK","WELCORP","DPWIRES","GROWW","DMART","PFOCUS","MRPL","ZENSAR","IDEA","SUZLON"]

SYMBOLS = get_symbols()
print(f"Scanning {len(SYMBOLS)}")

# --- 4. V51 + Volume Check - तुझ्या फोटो सारखा ---
results = []
for sym in SYMBOLS:
    token = token_map.get(sym)
    if not token: continue
    try:
        param = {
            "exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE",
            "fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d %H:%M"),
            "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        data = obj.getCandleData(param)
        if not data or not data['data']: continue

        df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema15'] = df['c'].ewm(span=15).mean()
        df['vwap'] = (df['c']*df['v']).cumsum()/df['v'].cumsum()
        df['vol20'] = df['v'].rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if abs(last['c']/prev['c']-1) > 0.15: continue
        if last['v'] < last['vol20']*1.5: continue

        long_c = last['ema9']>last['vwap'] and last['ema15']>last['vwap'] and last['ema9']>last['ema15'] and last['c']>last['vwap']
        short_c = last['ema9']<last['vwap'] and last['ema15']<last['vwap'] and last['ema9']<last['ema15'] and last['c']<last['vwap']

        if long_c:
            results.append(f"✅ {sym} LONG @ {round(last['c'],2)}")
        elif short_c:
            results.append(f"🔴 {sym} SHORT @ {round(last['c'],2)}")

    except: continue
    time.sleep(0.35)

if results:
    msg = f"V51 Smallcap 400 - {len(results)} Signals:\n" + "\n".join(results)
    requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
                  data={"chat_id":os.getenv('TELEGRAM_CHAT_ID'),"text":msg})
    print(msg)
else:
    print("DONE - Cross नाही - NO TRADE") 
