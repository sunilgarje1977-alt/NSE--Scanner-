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
        json={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

# === 500 SMALL CAP LIST - 50rs+ only ===
SYMBOLS = ["PGEL","BHEL","SAIL","IDEA","SUZLON","IRFC","RVNL","IREDA","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","NMDC","NATIONALUM","TATACHEM","ASHOKLEY","VOLTAS","BLUESTARCO","MARICO","UBL","MCDOWELL-N","RADICO","GODFRYPHLP","PATANJALI","APARINDS","KEI","THERMAX","FEDERALBNK","BANKINDIA","INDIANB","MAHABANK","IDBI","AUROPHARMA","LUPIN","GLENMARK","AJANTPHARM","BIOCON","AARTIIND","AEGISCHEM","ALKEM","ASTRAZEN","ASTERDM","BALKRISIND","BERGEPAINT","BSOFT","CUMMINSIND","ESCORTS","EXIDEIND","INDHOTEL","LINDEINDIA","MAXFIN","SUPREMEIND","BHARATFORG","PIRAMAL","UNOMINDA","TORNTPOWER","TIINDIA","SONACOMS","POLYCAB","HDFCAMC","COFORGE","BSE","MUTHOOTFIN","GMRAIRPORT","PAYTM","VMM","WAAREENER","360ONE","AAVAS","ACE","AFFLE","APLLTD","ALKYLAMINE","AMBER","ANGELONE","APTUS","AVANTIFEED","BEML","BLS","BALAMINES","BLUEDART","CHENNPETRO","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","IGL","IRB","GLAND","JBMA","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KANSAINER","KAYNES","KEC","KFINTECH","KPIL","M&MFIN","MANAPPURAM","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OBEROIRLTY","OLECTRA","PEL","PETRONET","PIIND","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","LICI","LODHA","LTF","AUBANK","ABCAPITAL","ADANIGREEN","ADANIPOWER","ATGL","AWL","BANKBARODA","BANDHANBNK","BATAINDIA","CANBK","CDSL","CENTRALBK","CGPOWER","CHOLAFIN","DABUR","DALBHARAT","DEEPAKNTR","DLF","DMART","GAIL","GODREJCP","GODREJPROP","HAVELLS","HINDPETRO","ICICIGI","IDFCFIRSTB","INDIGO","INDUSTOWER","IOC","IRCTC","JINDALSTEL","JKCEMENT","JSWSTEEL","KOTAKBANK","L&TFH","LALPATHLAB","LAURUSLABS","LICHSGFIN","LTIM","M&M","MANYAVAR","MFSL","MOTHERSON","MPHASIS","MRF","NAUKRI","OBEROIRLTY","OFSS","PAGEIND","PERSISTENT","PIDILITIND","PNB","POLYCAB","PVRINOX","RAMCOCEM","RBLBANK","SAIL","SBICARD","SIEMENS","SRF","SUNTV","TATACHEM","TATACOMM","TATAELXSI","TATAINVEST","TTML","VBL","VIPIND","WELCORP","WELSPUNLIV","WESTLIFE","WHIRLPOOL","ZEE","ZENSAR","AARTIIND","ABB","ABBOTINDIA","ABFRL","ACC","ADANIENT","ADANIPORTS","AMARAJABAT","AMBUJACEM","APOLLOHOSP","APOLLOTYRE","ASTRAL","ATUL","AUROPHARMA","BAJAJ-AUTO","BAJAJFINSV","BAJFINANCE","BALKRISIND","BALRAMCHIN","BATAINDIA","BEL","BERGEPAINT","BHARATFORG","BHEL","BIOCON","BOSCHLTD","BRITANNIA","CANFINHOME","CHAMBLFERT","CIPLA","COALINDIA","COLPAL","COROMANDEL","CROMPTON","CUB","DABUR","DEEPAKNTR","DELTACORP","DIXON","DMART","DRREDDY","EICHERMOT","EXIDEIND","FEDERALBNK","GAIL","GLENMARK","GMRINFRA","GODREJCP","GRANULES","GRASIM","GUJGASLTD","HAL","HAVELLS","HCLTECH","HDFCAMC","HEROMOTOCO","HINDALCO","HINDCOPPER","HINDUNILVR","ICICIGI","IDBI","IDFC","IEX","IGL","INDHOTEL","INDIACEM","INDIAMART","INDIGO","INDUSINDBK","INDUSTOWER","IPCALAB","ITC","JKCEMENT","JSWSTEEL","JUBLFOOD","LALPATHLAB","LAURUSLABS","LT","LTIM","LTTS","LUPIN","M&MFIN","MANAPPURAM","MARICO","MARUTI","MCDOWELL-N","MCX","METROPOLIS","MGL","MOTHERSON","MUTHOOTFIN","NAM-INDIA","NATIONALUM","NAUKRI","NAVINFLUOR","NMDC","NTPC","OBEROIRLTY","ONGC","PEL","PERSISTENT","PETRONET","PFIZER","PIDILITIND","PIIND","PNB","POWERGRID","RAMCOCEM","RBLBANK","RECLTD","SAIL","SBILIFE","SHREECEM","SRF","SUNPHARMA","TATACONSUM","TATAMOTORS","TATAPOWER","TATASTEEL","TECHM","TITAN","TORNTPHARM","TRENT","TVSMOTOR","UBL","ULTRACEMCO","UPL","VEDL","VOLTAS","WIPRO","ZEEL","DIXON","VOLTAS","KAYNES","PGEL","AMBER","SAFARI","CAMPUS","METROBRAND","BATAINDIA","RELAXO","LAOPALA","BOROSIL","CERA","KAJARIACER","SOMANY","GREENPANEL","CENTURYPLY","ASIANPAINT","BERGEPAINT","KANSAINER","INDIGO","SPICEJET","INDIAMART","JUSTDIAL","NAUKRI","INTELLECT","MASTEK","TANLA","ROUTE","HAPPSTMNDS","AFFLE","MAPMYINDIA","LTTS","TATAELXSI","KPITTECH","PERSISTENT","COFORGE","LTIM","BSOFT","MPHASIS","MUTHOOTFIN","MANAPPURAM","M&MFIN","LTF","CHOLAFIN","ABCAPITAL","AUBANK","FEDERALBNK","BANDHANBNK","RBLBANK","IDFCFIRSTB","BANKINDIA","INDIANB","MAHABANK","CENTRALBK","UCOBANK","BANKBARODA","CANBK","UNIONBANK","PSB","IOB","PNB","KARURVYSYA","CUB","DCBBANK","J&KBANK","SOUTHBANK","KARUR","EQUITAS","UJJIVAN","AUROPHARMA","GLENMARK","AJANTPHARM","NATCOPHARM","GRANULES","LAURUSLABS","DIVISLAB","CIPLA","DRREDDY","LUPIN","ALKEM","TORNTPHARM","ZYDUSLIFE","IPCALAB","JBCHEPHARM","PEL","ERIS","CAPLIPOINT","MEDANTA","MAXHEALTH","APOLLOHOSP","ASTERDM","FORTIS","LALPATHLAB","METROPOLIS","KIMS","RAINBOW","VIJAYA","SYNGENE","GLAND","GODFRYPHLP","RADICO","MCDOWELL-N","UBL","SULA","SOMDIST","PATANJALI","MARICO","DABUR","COLPAL","GODREJCP","EMAMILTD","BAJAJCON","HONASA","BIKAJI","VARUNBEV","VBL","TATACONSUM","NESTLEIND","BRITANNIA","JUBLFOOD","WESTLIFE","DEVYANI","SAPPHIRE","BARBEQUE","EIH","INDHOTEL","TAJGVK","CHALET","LEMONTREE","EASEMYTRIP","IRCTC","BLS","TBO","THOMASCOOK","CAMPUS","BATA","RELAXO","TRENT","DMART","V2RETAIL","VMART","ABFRL","SHOPERSTOP","ADITYA","RAYMOND","GOKEX","KPRMILL","WELSPUNLIV","WELCORP","TRIDENT","ALOKIND","VTL","INDIAMART","AFFLE","TANLA","ROUTE","NETWEB","KAYNES","DIXON","AMBER","PGEL","SYRMA","IKIO","AVALON","CYIENTDLM","DCXINDIA","MTARTECH","PNCINFRA","GRINFRA","KNRCON","NCC","NBCC","IRCON","RITES","RVNL","IRFC","HUDCO","NHPC","SJVN","IREDA","IRCTC","MAZDOCK","COCHINSHIP","GRSE","BEML","BDL","BEL","HAL","BHEL","BHARATFORG","ASTRA","PARAS","DATAPATTNS","IDEAFORGE","TATATECH","KPIT","LTTS"]

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

        curr = df.iloc[-1]
        ltp = float(curr['Close'])
        vol = float(curr['Volume'])

        # === तुझा FILTER ===
        if ltp < 50: return None # 50 रु पेक्षा कमी नको
        if vol < 20000: return None # 20000 volume पेक्षा कमी नको

        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()

        open_p = float(curr['Open'])
        ema9, ema15, vwap = float(curr['EMA9']), float(curr['EMA15']), float(curr['VWAP'])

        is_green = ltp > open_p
        price_above = ltp > ema9 and ltp > ema15 and ltp > vwap and ema9 > ema15

        if is_green and price_above:
            return f"🟢 {sym} @ {ltp:.1f} Vol {int(vol)} VWAP {vwap:.1f}"
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
    msg = f"🚀 *SmallCap 50rs+ Vol20k {now_str}* {len(SYMBOLS)} checked\n\n" + "\n".join(buys[:30])
else:
    msg = f"{now_str} - NO TRADE ({len(SYMBOLS)} smallcap 50rs+ Vol20k checked)"

send_tg(msg)
print(msg) 
