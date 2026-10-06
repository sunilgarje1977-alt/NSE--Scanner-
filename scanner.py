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
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e:
        print(e)

# Login
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK", ist_now())

# 500 Small Cap 50rs+ List
SYMBOLS = ["PGEL","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","NMDC","NATIONALUM","TATACHEM","ASHOKLEY","VOLTAS","BLUESTARCO","MARICO","UBL","MCDOWELL-N","RADICO","PATANJALI","APARINDS","KEI","THERMAX","FEDERALBNK","BANKINDIA","INDIANB","MAHABANK","IDBI","AUROPHARMA","LUPIN","GLENMARK","AJANTPHARM","BIOCON","AARTIIND","AEGISCHEM","ALKEM","ASTERDM","BALKRISIND","BSOFT","CUMMINSIND","ESCORTS","EXIDEIND","INDHOTEL","MAXFIN","SUPREMEIND","BHARATFORG","UNOMINDA","TORNTPOWER","TIINDIA","SONACOMS","POLYCAB","HDFCAMC","COFORGE","BSE","MUTHOOTFIN","GMRAIRPORT","PAYTM","VMM","WAAREENER","360ONE","AAVAS","ACE","AFFLE","APLLTD","ALKYLAMINE","AMBER","ANGELONE","APTUS","AVANTIFEED","BEML","BLS","BALAMINES","BLUEDART","CHENNPETRO","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","IGL","IRB","GLAND","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KANSAINER","KAYNES","KEC","KFINTECH","KPIL","M&MFIN","MANAPPURAM","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OBEROIRLTY","OLECTRA","PEL","PETRONET","PIIND","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","LICI","LODHA","LTF","AUBANK","ABCAPITAL","ADANIGREEN","ADANIPOWER","ATGL","BANKBARODA","BANDHANBNK","BATAINDIA","CANBK","CDSL","CENTRALBK","CGPOWER","CHOLAFIN","DABUR","DALBHARAT","DEEPAKNTR","DLF","DMART","GAIL","GODREJCP","GODREJPROP","HAVELLS","ICICIGI","IDFCFIRSTB","INDIGO","IOC","IRCTC","JKCEMENT","LALPATHLAB","LAURUSLABS","LTIM","MFSL","MOTHERSON","MPHASIS","NAM-INDIA","OBEROIRLTY","OFSS","PAGEIND","PERSISTENT","PIDILITIND","PNB","PVRINOX","RAMCOCEM","RBLBANK","SBICARD","SHREECEM","SRF","TATACOMM","TATAELXSI","TATAPOWER","TITAN","TORNTPHARM","UBL","ULTRACEMCO","UPL","VEDL","WIPRO","ZEEL","DIXON","KAJARIACER","CERA","SAFARI","CAMPUS","METROBRAND","RELAXO","BOROSIL","GREENPANEL","CENTURYPLY","INDIAMART","JUSTDIAL","INTELLECT","NETWEB","SYRMA","IKIO","AVALON","CYIENTDLM","DCXINDIA","DATAPATTNS","PARAS","IDEAFORGE","TATATECH","KPIT","ELECON","FSL","GPPL","HBLPOWER","HFCL","HSCL","IFCI","IEX","JWL","TEXRAIL","RAILTEL","RITES","CESC","GSPL","MGL","KPIGREEN","GENSOL","JUBLFOOD","EMAMILTD","HONASA","BIKAJI","VARUNBEV","VBL","DEVYANI","SAPPHIRE","BARBEQUE","EIH","CHALET","LEMONTREE","EASEMYTRIP","BLS","TBO","V2RETAIL","VMART","ABFRL","SHOPPERSTOP","RAYMOND","GOKEX","KPRMILL","WELSPUNLIV","WELCORP","ALOKIND","VTL","SOBHA","BRIGADE","ANANTRAJ","ADANIPOWER","JPOWER","ADANIGREEN","SUZLON","WAAREERTL","KARURVYSYA","CUB","DCBBANK","J&KBANK","SOUTHBANK","EQUITAS","UJJIVAN","CAPLIPOINT","ERIS","MEDANTA","MAXHEALTH","ASTERDM","FORTIS","KIMS","RAINBOW","VIJAYA","SULA","SOMDIST","GODFRYPHLP","RADICO","UBL","MCDOWELL-N","PATANJALI","MARICO","COLPAL","EMAMILTD","BAJAJCON","TATACONSUM","JUBLFOOD","WESTLIFE","EIH","INDHOTEL","CHALET","IRCTC","BLS","CAMPUS","BATA","TRENT","DMART","ABFRL","GOKEX","WELSPUNLIV","TRIDENT","INDIAMART","AFFLE","TANLA","ROUTE","MAPMYINDIA","LTTS","KPITTECH","PERSISTENT","COFORGE","LTIM","BSOFT","MUTHOOTFIN","MANAPPURAM","M&MFIN","LTF","CHOLAFIN","ABCAPITAL","AUBANK","FEDERALBNK","BANDHANBNK","RBLBANK","IDFCFIRSTB","BANKINDIA","INDIANB","MAHABANK","UCOBANK","BANKBARODA","CANBK","UNIONBANK","PSB","IOB","PNB","J&KBANK","SOUTHBANK","CUB","KARURVYSYA","UJJIVAN","EQUITAS","AUROPHARMA","GLENMARK","AJANTPHARM","NATCOPHARM","GRANULES","LAURUSLABS","DIVISLAB","CIPLA","DRREDDY","LUPIN","ALKEM","TORNTPHARM","ZYDUSLIFE","IPCALAB","JBCHEPHARM","ERIS","CAPLIPOINT","MEDANTA","MAXHEALTH","APOLLOHOSP","ASTERDM","FORTIS","LALPATHLAB","METROPOLIS","KIMS","SYNGENE","GLAND","RADICO","MCDOWELL-N","UBL","PATANJALI","MARICO","DABUR","GODREJCP","VARUNBEV","TATACONSUM","BRITANNIA","JUBLFOOD","EIH","INDHOTEL","IRCTC","BLS","TRENT","DMART","ABFRL","RAYMOND","WELSPUNLIV","TRIDENT","AFFLE","MAPMYINDIA","LTTS","TATAELXSI","COFORGE","LTIM","BSE","MCX","360ONE","KFINTECH","OLECTRA","WAAREENER","VMM","KAYNES","AMBER","PGEL","DIXON","SAFARI","CERA","KAJARIA","GREENPANEL","CENTURYPLY","BERGEPAINT","KANSAINER","INDIGO","SPICEJET","INTELLECT","MASTEK","TANLA","ROUTE","HAPPSTMNDS","NETWEB","KAYNES","DIXON","AMBER","SYRMA","AVALON","CYIENTDLM","MTARTECH","PNCINFRA","GRINFRA","KNRCON","NCC","NBCC","IRCON","RITES","RVNL","IRFC","HUDCO","NHPC","SJVN","IREDA","MAZDOCK","COCHINSHIP","GRSE","BEML","BDL","BEL","HAL","BHEL","BHARATFORG","ASTRA","PARAS","DATAPATTNS","IDEAFORGE","TATATECH","KPIT","LTTS","ELECON","FSL","GPPL","HBLPOWER","HFCL","HSCL","IFCI","IEX","IRB","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KANSAINER","KEC","KPIL","M&MFIN","MASTEK","MEDANTA","NATCOPHARM","OLECTRA","PNCINFRA","POLYCAB","RADICO","RITES","ROUTE","SAGAR","SONACOMS","SUNTV","SYNGENE","TANLA","TRIDENT","TTML","VBL","WELCORP","ZENSAR","ZOMATO","MAPMYINDIA","CYIENT","PEL","PETRONET","PNBHOUSING","PRESTIGE","PHOENIXLTD","SOBHA","BRIGADE","LODHA","GODREJPROP","DLF","OBEROIRLTY","ANANTRAJ","ADANIPOWER","TORNTPOWER","CESC","GSPL","IGL","MGL","IEX","WAAREERTL","SUZLON","KPIGREEN","GENSOL","WAAREEENER","JWL","TEXRAIL","RAILTEL","RVNL","IRCON","IRFC","RBLBANK","BANDHANBNK","FEDERALBNK","IDFCFIRSTB","BANKINDIA","MAHABANK","CENTRALBK","INDIANB","UCOBANK","BANKBARODA","CANBK","YESBANK","UNIONBANK","PSB"]

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

        # FILTERS
        if ltp < 50: return None
        if vol < 5000: return None

        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()

        ema9 = float(curr['EMA9'])
        ema15 = float(curr['EMA15'])
        vwap = float(curr['VWAP'])

        if ltp > ema9 and ltp > vwap:
            pct = (ltp/vwap-1)*100
            if pct > 0.3:
                return (pct, f"🟢 {sym} @ {ltp:.1f} VWAP+{pct:.1f}% Vol {int(vol/1000)}k")

    except:
        return None

results = []
with ThreadPoolExecutor(max_workers=20) as ex:
    futures = {ex.submit(analyze, s): s for s in set(SYMBOLS)}
    for f in as_completed(futures):
        r = f.result()
        if r: results.append(r)

results = sorted(results, key=lambda x: x[0], reverse=True)

now_str = ist_now().strftime("%d-%b %H:%M")
if results:
    top = "\n".join([x[1] for x in results[:25]])
    msg = f"🚀 *SmallCap 50+ | 5k Vol | {now_str}*\n{len(set(SYMBOLS))} checked\n\n{top}"
else:
    msg = f"{now_str} - NO TRADE ({len(set(SYMBOLS))} checked)"

send_tg(msg)
print(msg)
