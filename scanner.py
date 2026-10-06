import os, datetime, pytz, requests, pyotp, time
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
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except: pass

# Login
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK", ist_now())

# === 500 NSE STOCKS - FULL LIST WITH PGEL ===
SYMBOLS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","HINDUNILVR","ASIANPAINT","MARUTI","TITAN","AXISBANK","WIPRO","ULTRACEMCO","SUNPHARMA","ONGC","NTPC","POWERGRID","TATAMOTORS","TATASTEEL","JSWSTEEL","HINDALCO","COALINDIA","ADANIENT","ADANIPORTS","GRASIM","DIVISLAB","CIPLA","DRREDDY","EICHERMOT","BAJAJFINSV","BRITANNIA","NESTLEIND","HCLTECH","TECHM","SBILIFE","HDFCLIFE","ICICIPRULI","BAJAJ-AUTO","HEROMOTOCO","M&M","APOLLOHOSP","UPL","SHREECEM","INDUSINDBK","PGEL","PG ELECTROPLAST","BHEL","SAIL","IDEA","VODAFONEIDEA","YESBANK","SUZLON","IRFC","RVNL","IREDA","JIOFIN","JIOFINANCE","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","OILINDIA","NMDC","NATIONALUM","TATACHEM","TATACOMM","ASHOKLEY","MRF","SRF","VOLTAS","BLUESTARCO","COLPAL","MARICO","UBL","MCDOWELL-N","RADICO","GODFRYPHLP","PATANJALI","APARINDS","KEI","THERMAX","FEDERALBNK","BANKINDIA","INDIANB","MAHABANK","IDBI","AUROPHARMA","LUPIN","GLENMARK","AJANTPHARM","BIOCON","AARTIIND","AEGISCHEM","ALKEM","ASTRAZEN","ASTERDM","BALKRISIND","BERGEPAINT","BSOFT","BIRLASOFT","CUMMINSIND","ESCORTS","EXIDEIND","GSK","INDHOTEL","INDIANHOTEL","LINDEINDIA","MAXFIN","SCHAEFFLER","SUPREMEIND","BHARATFORG","GODREJIND","PIRAMAL","UNOMINDA","TORNTPOWER","TIINDIA","SONACOMS","POLYCAB","HDFCAMC","COFORGE","LTIM","PERSISTENT","MPHASIS","BSE","MUTHOOTFIN","GMRAIRPORT","ORACLE","MAXHEALTH","PAYTM","VMM","WAAREENER","SWIGGY","360ONE","AAVAS","ACE","AFFLE","APLLTD","ALKYLAMINE","AMBER","ANGELONE","APTUS","AVANTIFEED","BEML","BLS","BALAMINES","BLUEDART","CHENNPETRO","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","BAYERCROP","IGL","IRB","GLAND","JBMA","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KANSAINER","KAYNES","KEC","KFINTECH","KPIL","M&MFIN","MANAPPURAM","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OBEROIRLTY","OLECTRA","PEL","PETRONET","PIIND","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","LICI","LODHA","LTF","AUBANK","ABCAPITAL","ADANIGREEN","ADANIPOWER","ATGL","AWL","BANKBARODA","BANDHANBNK","BATAINDIA","BIOCON","CANBK","CDSL","CENTRALBK","CGPOWER","CHOLAFIN","DABUR","DALBHARAT","DEEPAKNTR","DIVISLAB","DLF","DMART","GAIL","GODREJCP","GODREJPROP","HAVELLS","HINDPETRO","ICICIGI","IDFCFIRSTB","IGL","INDIGO","INDUSTOWER","IOC","IRCTC","JINDALSTEL","JSWENERGY","JUBLFOOD","KOTAKBANK","LAURUSLABS","LICHSGFIN","LTIM","LUPIN","M&M","MANYAVAR","MCDOWELL-N","MFSL","MOTHERSON","MPHASIS","MRF","MUTHOOTFIN","NAUKRI","NMDC","NTPC","OBEROIRLTY","OFSS","ONGC","PAGEIND","PEL","PERSISTENT","PETRONET","PIDILITIND","PIIND","PNB","POLYCAB","POWERGRID","PVRINOX","RAMCOCEM","RECLTD","RELIANCE","SAIL","SBICARD","SBILIFE","SHREECEM","SIEMENS","SRF","SUNPHARMA","TATACONSUM","TATAMOTORS","TATAPOWER","TATASTEEL","TCS","TECHM","TITAN","TORNTPHARM","TRENT","TVSMOTOR","UBL","ULTRACEMCO","UPL","VEDL","VOLTAS","WIPRO","ZEEL","ZYDUSLIFE","TATACHEM","TATACOMM","TATAELXSI","TATAINVEST","TTML","VBL","VARUNBEV","VEDANTA","VIJAYA","VINATIORGA","VIPIND","VOLTAS","VTL","WELCORP","WELSPUNLIV","WESTLIFE","WHIRLPOOL","ZEE","ZENSAR","ZOMATO","AARTIIND","ABB","ABBOTINDIA","ABCAPITAL","ABFRL","ACC","ADANIENT","ADANIPORTS","ALKEM","AMARAJABAT","AMBUJACEM","APOLLOHOSP","APOLLOTYRE","ASHOKLEY","ASTRAL","ATUL","AUBANK","AUROPHARMA","BAJAJ-AUTO","BAJAJFINSV","BAJAJHLDNG","BAJFINANCE","BALKRISIND","BALRAMCHIN","BANDHANBNK","BANKBARODA","BATAINDIA","BEL","BERGEPAINT","BHARATFORG","BHARTIARTL","BHEL","BIOCON","BOSCHLTD","BRITANNIA","BSOFT","CANBK","CANFINHOME","CHAMBLFERT","CHOLAFIN","CIPLA","COALINDIA","COFORGE","COLPAL","CONCOR","COROMANDEL","CROMPTON","CUB","CUMMINSIND","DABUR","DALBHARAT","DEEPAKNTR","DELTACORP","DIVISLAB","DIXON","DLF","DMART","DRREDDY","EICHERMOT","ESCORTS","EXIDEIND","FEDERALBNK","GAIL","GLENMARK","GMRINFRA","GODREJCP","GODREJPROP","GRANULES","GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCAMC","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDCOPPER","HINDPETRO","HINDUNILVR","ICICIBANK","ICICIGI","ICICIPRULI","IDBI","IDEA","IDFC","IDFCFIRSTB","IEX","IGL","INDHOTEL","INDIACEM","INDIAMART","INDIGO","INDUSINDBK","INDUSTOWER","INFY","IOC","IPCALAB","IRCTC","ITC","JINDALSTEL","JKCEMENT","JSWSTEEL","JUBLFOOD","KOTAKBANK","L&TFH","LALPATHLAB","LAURUSLABS","LICHSGFIN","LT","LTIM","LTTS","LUPIN","M&M","M&MFIN","MANAPPURAM","MARICO","MARUTI","MCDOWELL-N","MCX","METROPOLIS","MFSL","MGL","MOTHERSON","MPHASIS","MRF","MUTHOOTFIN","NAM-INDIA","NATIONALUM","NAUKRI","NAVINFLUOR","NESTLEIND","NMDC","NTPC","OBEROIRLTY","OFSS","ONGC","PAGEIND","PEL","PERSISTENT","PETRONET","PFIZER","PIDILITIND","PIIND","PNB","POLYCAB","POWERGRID","PVRINOX","RAMCOCEM","RBLBANK","RECLTD","RELIANCE","SAIL","SBICARD","SBILIFE","SBIN","SHREECEM","SIEMENS","SRF","SUNPHARMA","SUNTV","TATACHEM","TATACOMM","TATACONSUM","TATAELXSI","TATAMOTORS","TATAPOWER","TATASTEEL","TCS","TECHM","TITAN","TORNTPHARM","TRENT","TVSMOTOR","UBL","ULTRACEMCO","UPL","VEDL","VOLTAS","WIPRO","ZEEL","ZYDUSLIFE"]

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
        if len(df) < 25: return None
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        curr, prev = df.iloc[-1], df.iloc[-2]
        ltp, open_p = float(curr['Close']), float(curr['Open'])
        if ltp < 20: return None
        vol = float(curr['Volume']); avg_vol = df['Volume'].iloc[-21:-1].mean()
        volx = vol/(avg_vol+1)
        ema9, ema15, vwap = float(curr['EMA9']), float(curr['EMA15']), float(curr['VWAP'])
        ema9_prev, ema15_prev = float(prev['EMA9']), float(prev['EMA15'])
        vwap_prev = float(prev['VWAP'])
        # ITC PATTERN
        is_green = ltp > open_p
        price_above = ltp > ema9 and ltp > ema15 and ltp > vwap
        vwap_cross = float(prev['Close']) < vwap_prev and ltp > vwap
        ema_cross = ema9 > ema15 and ema9_prev <= ema15_prev
        if is_green and volx >= 1.0 and price_above and (vwap_cross or ema_cross or ltp > vwap*1.002):
            return f"🟢 {sym} BUY @ {ltp:.1f} VWAP {vwap:.1f} EMA9 {ema9:.1f} Vol {volx:.1f}x"
    except:
        return None

buys=[]
with ThreadPoolExecutor(max_workers=15) as ex:
    futures = {ex.submit(analyze, s): s for s in SYMBOLS}
    for f in as_completed(futures):
        res = f.result()
        if res: buys.append(res)

now_str = ist_now().strftime("%d-%b %H:%M")
if buys:
    msg = f"📊 *ITC Pattern {now_str}* 5m {len(SYMBOLS)} stocks\n\n" + "\n".join(buys[:20])
else:
    msg = f"{now_str} - NO TRADE ({len(SYMBOLS)} checked) - ITC Pattern"

send_tg(msg)
print(msg)
