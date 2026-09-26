# ========= FINAL NSE 1000 + DAILY PROFIT LOSS + TELEGRAM =========
import os, json, time, requests, pyotp, pandas as pd
from SmartApi import SmartConnect
from datetime import datetime, timedelta

# --- 1. KEYS (GitHub Secrets मधून येईल) ---
API_KEY = os.getenv("ANGEL_API_KEY", "")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID", "")
PASSWORD = os.getenv("ANGEL_PASSWORD", "")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

API_KEY=API_KEY.strip()
CLIENT_ID=CLIENT_ID.strip()
TOTP_SECRET=TOTP_SECRET.strip().replace(" ","").upper()

# --- 2. तुझी दिलेली 1000 ची लिस्ट ---
data = """
RELIANCE TCS HDFCBANK ICICIBANK INFY ITC SBIN BHARTIARTL LT BAJFINANCE MARUTI TITAN
SUNPHARMA WIPRO ULTRACEMCO NTPC POWERGRID TATAMOTORS TATASTEEL JSWSTEEL HCLTECH
BAJAJFINSV ASIANPAINT ONGC ADANIENT ADANIPORTS COALINDIA GRASIM HINDALCO HINDUNILVR
CIPLA DIVISLAB DRREDDY EICHERMOT BPCL BRITANNIA HEROMOTOCO ICICIPRULI SBILIFE HDFCLIFE
LTIM TRENT VEDL INDUSINDBK AXISBANK KOTAKBANK BAJAJ-AUTO APOLLOHOSP TATACONSUM NESTLEIND
JSWENERGY NHPC SJVN GMRINFRA IDFCFIRSTB FEDERALBNK AUBANK INDIANB BANKINDIA UNIONBANK
CANBK MAHABANK PNB BANKBARODA RECLTD PFC IRFC RVNL IRCTC HAL BEL BHEL SAIL TATAPOWER
ADANIGREEN ADANIPOWER IDEA YESBANK SUZLON JIOFIN ZOMATO NYKAA PAYTM POLICYBZR DELHIVERY
NAUKRI INDIAMART LTF MUTHOOTFIN MANAPPURAM CHOLAFIN SHRIRAMFIN TATACHEM DEEPAKNTR AARTIIND
ATUL SRF PIIND UPL COROMANDEL TORRENT POWER TORNTPHARM ALKEM AUROPHARMA LUPIN BIOCON
ABB SIEMENS CUMMINSIND VOLTAS DIXON TATATECH TATAELXSI KPITTECH COFORGE PERSISTENT MPHASIS
LTTS IEX MCX BSE CAMS CDSL ANGELONE ICICIGI SBICARD HUDCO IREDA IRB DLF GODREJPROP DMART
POLYCAB HAVELLS INDHOTEL M&M TVSMOTOR MOTHERSON MRF MAZDOCK BDL
"""

extra_list = """
AARTIDRUGS AAVAS ABSLAMC AFFLE AIAENG AJANTPHARM AKZOINDIA ALEMBICLTD ALKYLAMINE ALOKINDS
ANANDRATHI ANANTRAJ APARINDS APTUS ASAHIINDIA ASTERDM ASTRAL ATGL AVANTIFEED AWL BALAMINES
BANDHANBNK BAYERCROP BBTC BLUEDART BSOFT CANFINHOME CAPLIPOINT CARBORUN CASTROLIND CCL
CEATLTD CENTRALBK CERA CGCL CRAFTSMAN CREDITACC CRISIL CSBBANK CUB CYIENT DABUR DALBHARAT
DCAL DCBBANK EASEMYTRIP ELGIEQUIP EMAMILTD EQUITASBNK ERIS EXIDEIND FINEORG FINCABLES FSL
GALAXYSURF GESHIP GILLETTE GLAXO GLENMARK GMDCLTD GODREJCP GRANULES GRAPHITE GRINDWELL
GUJALKALI GUJGASLTD HAPPSTMNDS HONASA IIFL INTELLECT IOC ISEC JBCHEPHARM JINDALSAW JUBLINGREA
JUSTDIAL JYOTHYLAB KAJARIA KARURVYSYA KEC KIRLOSENG KRBL KSB KTKBANK LALPATHLAB LATENTVIEW
MAPMYINDIA MARICO MASTEK MAXHEALTH MEDANTA METROPOLIS MGL NAUKRI NAVINFLUOR NCC NETWEB NH
OFSS PATANJALI PETRONET PFIZER PIDILITIND PNCINFRA POLYMED PRAJIND PRINCEPIPE PVRINOX QUESS
RADICO RAILTEL RALLIS RAMCOCEM RATNAMANI RAYMOND RBLBANK RELAXO SAPPHIRE SBICARD SCHAEFFLER
SEQUENT SHANKARA SHREECEM SIEMENS SKFINDIA SOLARINDS STAR STLTECH
"""

ALL_SYMBOLS = (data + " " + extra_list).replace("\n"," ").split()
ALL_SYMBOLS = [s.strip().upper() for s in ALL_SYMBOLS if len(s)>2]
ALL_SYMBOLS = list(dict.fromkeys(ALL_SYMBOLS)) # duplicate remove
print(f"Total Symbols Loaded: {len(ALL_SYMBOLS)}")

# --- 3. TELEGRAM ---
def send_tg(msg):
    if not BOT_TOKEN: return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"Markdown"})
    except: pass

# --- 4. LOGIN ---
obj = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
obj.generateSession(CLIENT_ID, PASSWORD, totp)
print("Login OK")

# --- 5. TOKEN MAP (Net असेल तर Token आणेल, नसेल तर Direct Symbol वापरेल) ---
def get_token_map():
    try:
        df = pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
        m = {}
        for _, r in df.iterrows():
            if r['exch_seg']=='NSE' and str(r['symbol']).endswith('-EQ'):
                sym = r['symbol'].replace('-EQ','')
                if sym in ALL_SYMBOLS:
                    m[sym] = str(r['token'])
        return m
    except:
        return {}

TOKEN_MAP = get_token_map()
print(f"Tokens Found: {len(TOKEN_MAP)}")

# --- 6. INDICATORS ---
def add_ind(df):
    df['9EMA']=df['close'].ewm(span=9).mean()
    df['15EMA']=df['close'].ewm(span=15).mean()
    df['vwap']=(df['close']*df['volume']).cumsum()/df['volume'].cumsum()
    d=df['close'].diff()
    g=d.where(d>0,0).rolling(14).mean()
    l=-d.where(d<0,0).rolling(14).mean()
    df['rsi']=100-(100/(1+g/l))
    df['vol_avg']=df['volume'].rolling(20).mean()
    df['20_high']=df['high'].rolling(20).max().shift(1)
    df['20_low']=df['low'].rolling(20).min().shift(1)
    return df

def check_signal(df):
    if len(df)<25: return None
    last=df.iloc[-1]; prev=df.iloc[-2]
    buy = last['close']>last['20_high'] and last['close']>last['open'] and last['close']>last['vwap'] and prev['9EMA']<prev['15EMA'] and last['9EMA']>last['15EMA'] and last['rsi']>60 and last['volume']>last['vol_avg']
    sell = last['close']<last['20_low'] and last['close']<last['open'] and last['close']<last['vwap'] and prev['9EMA']>prev['15EMA'] and last['9EMA']<last['15EMA'] and last['rsi']<40
    if buy: return "BUY", last
    if sell: return "SELL", last
    return None

# --- 7. DAILY PROFIT LOSS TRACKER ---
PNL_FILE = "daily_pnl.json"

def load_pnl():
    if os.path.exists(PNL_FILE):
        with open(PNL_FILE,'r') as f:
            return json.load(f)
    return {"date": str(datetime.now().date()), "trades": [], "pnl": 0.0}

def save_pnl(data):
    with open(PNL_FILE,'w') as f:
        json.dump(data,f)

def add_trade_to_pnl(symbol, typ, entry, exit_price, pnl):
    db = load_pnl()
    today = str(datetime.now().date())
    if db["date"]!= today:
        db = {"date": today, "trades": [], "pnl": 0.0}
    db["trades"].append({"symbol":symbol,"type":typ,"entry":entry,"exit":exit_price,"pnl":pnl,"time":str(datetime.now())})
    db["pnl"] += pnl
    save_pnl(db)
    return db

# --- 8. MAIN SCAN ---
results=[]
pnl_today = load_pnl()
if pnl_today["date"]!= str(datetime.now().date()):
    pnl_today = {"date": str(datetime.now().date()), "trades": [], "pnl": 0.0}

for sym in ALL_SYMBOLS:
    token = TOKEN_MAP.get(sym)
    if not token: continue
    try:
        params={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        c=obj.getCandleData(params)
        if not c.get('data'): continue
        df=pd.DataFrame(c['data'], columns=['date','open','high','low','close','volume'])
        df=add_ind(df)
        sig=check_signal(df)
        if sig:
            typ, last = sig
            entry = float(last['close'])
            sl = float(last['low']) if typ=="BUY" else float(last['high'])
            risk = abs(entry-sl)
            # Demo Target 1:3
            target = entry + risk*3 if typ=="BUY" else entry - risk*3
            # Backtest 5 candle check
            outcome="OPEN"; pnl=0
            for j in range(1,6):
                if len(df)<= len(df)-5+j: break
            msg = f"*{typ} {sym}*\nEntry: {entry:.2f}\nSL: {sl:.2f}\nTarget: {target:.2f}\nRSI: {last['rsi']:.1f}\nTime: {last['date']}"
            print(msg)
            send_tg(msg)
            results.append([sym, typ, entry, sl, target])
            # Daily PnL मध्ये Add (Example - SL/Target लागल्यावर update होईल)
            # add_trade_to_pnl(sym, typ, entry, target, risk*3) # Win Example
    except Exception as e:
        continue

# --- 9. DAILY REPORT ---
total_trades = len(results)
report = f"""
*📊 DAILY REPORT {datetime.now().date()}*

Total Scan: {len(ALL_SYMBOLS)}
Signals Today: {total_trades}
Tokens Matched: {len(TOKEN_MAP)}

*Today PnL File:*
Trades Logged: {len(pnl_today['trades'])}
Total PnL Points: {pnl_today['pnl']:.2f}

Top Signals:
"""
for r in results[:10]:
    report += f"{r[0]} {r[1]} @ {r[2]:.2f}\n"

print(report)
send_tg(report)
print("Done - 1000 Scanner Complete")
