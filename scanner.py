import os, datetime, pytz, requests, pyotp, glob
import pandas as pd
from SmartApi import SmartConnect

# --- Secrets ---
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PWD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")
TELE_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELE_CHAT = os.getenv("TELEGRAM_CHAT_ID")

IST = pytz.timezone('Asia/Kolkata')
def ist_now(): return datetime.datetime.now(IST)
def send_tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage",
        json={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"})
        print(msg)
    except Exception as e: print(e)

# --- Login ---
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK - ITC Pattern 500 Scanner")

# --- 500 LIST (Midcap 150 + Smallcap 250 + Extra) ---
MID_SMALL_500 = [
"ITC","URBANCO","ASHOKLEY","BALKRISIND","BERGEPAINT","BHARATFORG","BLUESTARCO","ABBOTINDIA","EXIDEIND","COLPAL","COROMANDEL",
"ESCORTS","GSK","HEROMOTOCO","INDHOTEL","LINDEINDIA","TATACOMM","MAXFIN","MRF","SCHAEFFLER","SHREECEM","SRF","SUPREMEIND","VOLTAS",
"GODFRYPHLP","PATANJALI","GODREJIND","PIRAMAL","APARINDS","RADICO","SAIL","NLCINDIA","NATIONALUM","BHEL","LUPIN","FEDERALBNK",
"AUROPHARMA","KEI","THERMAX","OIL","INDUSINDBK","MAHABANK","BANKINDIA","INDIANB","NMDC","APLAPOLLO","MARICO","OFSS","AJANTPHARM","BIOCON",
"GLENMARK","BSE","YESBANK","WAAREENER","VMM","UPL","UNOMINDA","MCDOWELL-N","UBL","TIINDIA","TORNTPOWER","SWIGGY","SUZLON","CUMMINSIND",
"MUTHOOTFIN","GMRAIRPORT","POLYCAB","HDFCAMC","INDUSTOWER","COFORGE","SONACOMS","ORACLE","IDBI","MPHASIS","MAXHEALTH","LTIM","PERSISTENT","PAYTM",
"360ONE","AARTIIND","AAVAS","ACE","AEGISCHEM","AETHER","AFFLE","APLLTD","ALKYLAMINE","ALLCARGO","ALOKINDS","ARE&M","AMBER","ANANDRATHI",
"ANGELONE","ANURAS","APTUS","ACI","ASAHIINDIA","ASTERDM","ASTRAZEN","AVANTIFEED","BEML","BLS","BALAMINES","BALRAMCHIN","BIKAJI","BIRLACORPN",
"BSOFT","BLUEDART","BBTC","CHENNPETRO","IRCON","KSB","SANSERA","DBREALTY","KPITTECH","TATAELXSI","LTTS","TATACHEM","CONCOR","PRESTIGE",
"PHOENIXLTD","SBICARD","BAYERCROP","IGL","IRB","GLAND","JBMA","JINDALSTEL","JSL","JSWENERGY","JSWINFRA","JUBLFOOD","KALYANKJIL","KANSAINER",
"KAYNES","KEC","KFINTECH","KPIL","KRBL","M&MFIN","MANAPPURAM","MASTEK","MCX","MEDANTA","METROPOLIS","MFSL","MGL","MINDACORP","NATCOPHARM",
"NAUKRI","NBCC","NCC","NH","NHPC","NTPC","OBEROIRLTY","OIL","OLECTRA","PEL","PETRONET","PIDILITIND","PIIND","PNBHOUSING","POLYCAB",
"POWERINDIA","RECLTD","SIEMENS","SRF","SUNTV","SYNGENE","TIINDIA","TRENT","TRIDENT","UPL","WELCORP","ZYDUSLIFE","ZOMATO","NYKAA","DELHIVERY",
"MAPMYINDIA","IDEA","JIOFIN","IREDA","RVNL","IRFC","SJVN","HUDCO","PNCINFRA","GRINFRA","MAZDOCK","GRSE","HAL","BEL","BDL","MTARTECH",
"CYIENT","TANLA","ROUTE","HAPPSTMNDS","INTELLECT","TECHM","WIPRO","AADHARHFC","ABREL","ACME","AEGISLOG","STLTECH","CUPID","NAVINFLUOR",
"POONAWALLA","EMCURE","HFCL","LICI","ICICIPRULI","LODHA","LENSKART","LGEL","GROWW","LTF","AUBANK","ABCAPITAL","AIAENG","3MINDIA","DATAPATTNS",
"FINCABLES","LATENTVIEW","CARTRADE","EASEMYTRIP","GENSOL","POWERMECH","TRIVENI","PRAJIND","COCHINSHIP","AVANTEL","ASTRAMICRO","CENTUM"
]

# CSV मधले पण add
try:
    for f in glob.glob("*.csv"):
        df = pd.read_csv(f)
        for col in df.columns:
            if 'symbol' in col.lower():
                MID_SMALL_500.extend(df[col].astype(str).str.upper().tolist())
except: pass

symbols = list(dict.fromkeys([s.strip().upper() for s in MID_SMALL_500 if len(s.strip())>2]))[:500]
print(f"Loaded {len(symbols)} symbols")

def get_token(sym):
    try:
        r = smart.searchScrip("NSE", sym)
        if r and r.get('data'): return r['data'][0]['symboltoken']
    except: return None

def analyze(sym):
    try:
        token = get_token(sym)
        if not token: return None
        from_date = (ist_now() - datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        to_date = ist_now().strftime("%Y-%m-%d %H:%M")
        hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_date,"todate":to_date})
        if not hist or not hist.get('data'): return None
        df = pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        if len(df) < 40: return None
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)

        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()

        curr = df.iloc[-1]; prev = df.iloc[-2]; prev2 = df.iloc[-3]
        ltp = float(curr['Close']); open_p = float(curr['Open'])
        vol = float(curr['Volume']); avg_vol = df['Volume'].iloc[-21:-1].mean()
        volx = vol / (avg_vol + 1)
        if ltp < 20: return None

        is_green = ltp > open_p
        ema9 = float(curr['EMA9']); ema9_prev = float(prev['EMA9'])
        ema15 = float(curr['EMA15']); ema15_prev = float(prev['EMA15'])
        vwap = float(curr['VWAP']); vwap_prev = float(prev['VWAP'])

        vwap_cross_up = (float(prev['Close']) < vwap_prev and ltp > vwap) or (ema9_prev < vwap_prev and ema9 > vwap)
        ema_cross_up = ema9 > ema15 and ema9_prev <= ema15_prev
        price_above_all = ltp > ema9 and ltp > ema15 and ltp > vwap
        vol_breakout = volx >= 1.5 and vol > 5000

        if is_green and vol_breakout and price_above_all and (vwap_cross_up or ema_cross_up):
            if float(prev['Close']) < float(prev['EMA9']) or float(prev2['Close']) < float(prev2['VWAP']):
                return {"type":"BUY","symbol":sym,"ltp":ltp,"sl":round(ltp*0.985,2),"tp":round(ltp*1.03,2),"volx":round(volx,2)}

        # SELL
        if ltp < open_p and volx >=1.5 and ltp < vwap and ema9 < ema15:
            if float(prev['Close']) > vwap_prev:
                return {"type":"SELL","symbol":sym,"ltp":ltp,"sl":round(ltp*1.015,2),"tp":round(ltp*0.97,2),"volx":round(volx,2)}
        return None
    except: return None

buys=[]; sells=[]
for i,sym in enumerate(symbols[:400]): # GitHub 6min limit
    r = analyze(sym)
    if r:
        (buys if r['type']=='BUY' else sells).append(r)
        print(f"FOUND {r}")
    if i%50==0: print(f"{i}/{len(symbols)} scanned")

now_str = ist_now().strftime("%d-%b %H:%M")
if buys or sells:
    msg = f"📊 *ITC Pattern {now_str}* 5m VWAP Cross 9/15 + Green + Vol\nChecked {len(symbols)} Mid+Small 500\n\n"
    for b in buys[:10]: msg+=f"🟢 BUY {b['symbol']} @ {b['ltp']:.2f} SL {b['sl']} TP {b['tp']} Vol {b['volx']}x\n"
    for s in sells[:10]: msg+=f"🔴 SELL {s['symbol']} @ {s['ltp']:.2f} SL {s['sl']} TP {s['tp']} Vol {s['volx']}x\n"
    send_tg(msg)
else:
    send_tg(f"{now_str} - NO TRADE ({len(symbols)}) - ITC Pattern Not Found - Vol>1.5x")
