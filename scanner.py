import os, datetime, pytz, requests, pyotp
import pandas as pd
from SmartApi import SmartConnect
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        json={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

# 200 FAST LIST - Mid+Smallcap
SYMBOLS = ["ITC","BHEL","SAIL","IDEA","YESBANK","SUZLON","IRFC","RVNL","IREDA","JIOFIN","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","NMDC","NATIONALUM","TATACHEM","TATACOMM","ASHOKLEY","MRF","SRF","VOLTAS","BLUESTARCO","COLPAL","MARICO","UBL","MCDOWELL-N","RADICO","GODFRYPHLP","PATANJALI","APARINDS","KEI","THERMAX","FEDERALBNK","BANKINDIA","INDIANB","MAHABANK","IDBI","AUROPHARMA","LUPIN","GLENMARK","AJANTPHARM","BIOCON","AARTIIND","AEGISCHEM","ALKEM","ASTRAZEN","ASTERDM","BALKRISIND","BERGEPAINT","BSOFT","CUMMINSIND","ESCORTS","EXIDEIND","GSK","HEROMOTOCO","INDHOTEL","LINDEINDIA","MAXFIN","SCHAEFFLER","SHREECEM","SUPREMEIND","BHARATFORG","GODREJIND","PIRAMAL","UPL","UNOMINDA","TORNTPOWER","TIINDIA","SONACOMS","POLYCAB","HDFCAMC","COFORGE","LTIM","PERSISTENT","MPHASIS","BSE","MUTHOOTFIN","GMRAIRPORT","ORACLE","MAXHEALTH","PAYTM","VMM","WAAREENER","SWIGGY","360ONE","AAVAS","ACE","AFFLE","APLLTD","ALKYLAMINE","AMBER","ANGELONE","APTUS","AVANTIFEED","BEML","BLS","BALAMINES","BLUEDART","CHENNPETRO","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","BAYERCROP","IGL","IRB","GLAND","JBMA","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KANSAINER","KAYNES","KEC","KFINTECH","KPIL","M&MFIN","MANAPPURAM","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OBEROIRLTY","OLECTRA","PEL","PETRONET","PIIND","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","TECHM","WIPRO","HFCL","LICI","ICICIPRULI","LODHA","LTF","AUBANK","ABCAPITAL"][:200]

def analyze(sym):
    try:
        r = smart.searchScrip("NSE", sym)
        if not r or not r.get('data'): return None
        token = r['data'][0]['symboltoken']
        from_date = (ist_now() - datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
        to_date = ist_now().strftime("%Y-%m-%d %H:%M")
        hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_date,"todate":to_date})
        if not hist or not hist.get('data'): return None
        df = pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        if len(df) < 30: return None
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        curr, prev = df.iloc[-1], df.iloc[-2]
        ltp, open_p = float(curr['Close']), float(curr['Open'])
        vol = float(curr['Volume']); avg_vol = df['Volume'].iloc[-21:-1].mean()
        if ltp < 20 or avg_vol < 1000: return None
        volx = vol/(avg_vol+1)
        ema9, ema9_prev = float(curr['EMA9']), float(prev['EMA9'])
        ema15, ema15_prev = float(curr['EMA15']), float(prev['EMA15'])
        vwap, vwap_prev = float(curr['VWAP']), float(prev['VWAP'])
        is_green = ltp > open_p
        price_above = ltp > ema9 and ltp > ema15 and ltp > vwap
        vwap_cross = float(prev['Close']) < vwap_prev and ltp > vwap
        ema_cross = ema9 > ema15 and ema9_prev <= ema15_prev
        if is_green and volx >= 1.2 and price_above and (vwap_cross or ema_cross):
            return f"🟢 BUY {sym} @ {ltp:.2f} SL {ltp*0.985:.2f} TP {ltp*1.03:.2f} Vol {volx:.1f}x"
    except: return None

buys=[]
with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(analyze, s): s for s in SYMBOLS}
    for f in as_completed(futures):
        res = f.result()
        if res: buys.append(res)

now_str = ist_now().strftime("%d-%b %H:%M")
if buys:
    msg = f"📊 *ITC Pattern {now_str}* 5m VWAP 9/15\n\n" + "\n".join(buys[:15])
else:
    msg = f"{now_str} - NO TRADE (200 checked) - ITC Pattern"

send_tg(msg)
print(msg)
