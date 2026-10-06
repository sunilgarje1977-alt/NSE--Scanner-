import os, datetime, pytz, requests, pyotp, time
import pandas as pd
import numpy as np
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
def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", json={"chat_id": TELE_CHAT, "text": m, "parse_mode":"Markdown"}, timeout=15)
    except Exception as e: print(e)

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK", ist_now())

# BSE 1000 Small Cap (Angel NSE token ने चालतील)
SYMBOLS = ["PGEL","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","NMDC","NATIONALUM","TATACHEM","ASHOKLEY","VOLTAS","BLUESTARCO","MARICO","UBL","MCDOWELL-N","RADICO","PATANJALI","APARINDS","KEI","FEDERALBNK","BANKINDIA","INDIANB","MAHABANK","IDBI","AUROPHARMA","LUPIN","GLENMARK","BIOCON","AARTIIND","ALKEM","BALKRISIND","BSOFT","CUMMINSIND","ESCORTS","EXIDEIND","INDHOTEL","SUPREMEIND","BHARATFORG","UNOMINDA","TORNTPOWER","SONACOMS","POLYCAB","HDFCAMC","COFORGE","BSE","MUTHOOTFIN","PAYTM","VMM","WAAREENER","360ONE","AAVAS","ACE","AFFLE","AMBER","ANGELONE","BEML","BLS","BLUEDART","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","IRB","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KAYNES","KEC","KFINTECH","M&MFIN","MANAPPURAM","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OBEROIRLTY","OLECTRA","PEL","PIIND","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","LICI","LODHA","LTF","AUBANK","ADANIGREEN","ADANIPOWER","BANKBARODA","BANDHANBNK","BATAINDIA","CANBK","CDSL","CGPOWER","CHOLAFIN","DABUR","DLF","DMART","GAIL","GODREJCP","GODREJPROP","HAVELLS","IDFCFIRSTB","INDIGO","IOC","IRCTC","LALPATHLAB","LAURUSLABS","LTIM","MOTHERSON","MPHASIS","OFSS","PAGEIND","PERSISTENT","PNB","PVRINOX","RBLBANK","SRF","TATACOMM","TATAPOWER","TITAN","UBL","VEDL","DIXON","SAFARI","CAMPUS","METROBRAND","BOROSIL","GREENPANEL","INDIAMART","INTELLECT","NETWEB","SYRMA","AVALON","DATAPATTNS","PARAS","TATATECH","ELECON","HFCL","IEX","JWL","TEXRAIL","RAILTEL","RITES","CESC","MGL","WAAREERTL","VARUNBEV","VBL","DEVYANI","CHALET","EASEMYTRIP","V2RETAIL","VMART","ABFRL","RAYMOND","WELSPUNLIV","SOBHA","BRIGADE","ANANTRAJ","JPOWER","KARURVYSYA","CUB","UJJIVAN","EQUITAS","FORTIS","KIMS","SULA","GODFRYPHLP","GRANULES","DIVISLAB","CIPLA","DRREDDY","IPCALAB","JBCHEPHARM","ERIS","CAPLIPOINT","MAXHEALTH","APOLLOHOSP","ASTERDM","LALPATHLAB","METROPOLIS","SYNGENE","GLAND","COLPAL","EMAMILTD","BAJAJCON","TATACONSUM","BRITANNIA","EIH","CHALET","BLS","TRENT","DMART","GOKEX","WELSPUNLIV","AFFLE","MAPMYINDIA","LTTS","PERSISTENT","360ONE","KFINTECH","OLECTRA","KAYNES","AMBER","DIXON","SAFARI","CERA","KAJARIA","GREENPANEL","CENTURYPLY","BERGEPAINT","KANSAINER","INTELLECT","MASTEK","NETWEB","AVALON","CYIENTDLM","MTARTECH","PNCINFRA","KNRCON","RAILTEL","RITES","RVNL","IRFC","HUDCO","NHPC","SJVN","IREDA","MAZDOCK","COCHINSHIP","BEML","BDL","BHARATFORG","ASTRA","IDEAFORGE","ELECON","FSL","GPPL","HBLPOWER","IFCI","INDHOTEL","JINDALSTEL","JSL","JSWENERGY","KEC","KPIL","MEDANTA","OLECTRA","PNCINFRA","POLYCAB","RADICO","ROUTE","SONACOMS","SUNTV","TTML","WELCORP","ZENSAR","ZOMATO","CYIENT","PEL","PETRONET","PRESTIGE","PHOENIXLTD","SOBHA","BRIGADE","LODHA","GODREJPROP","DLF","TORNTPOWER","CESC","GSPL","IGL","KPIGREEN","WAAREEENER","JWL","TEXRAIL","RAILTEL","BANDHANBNK","RBLBANK","IDFCFIRSTB","BANKINDIA","MAHABANK","UCOBANK","YESBANK","UNIONBANK"]

def calc_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze(sym):
    try:
        time.sleep(0.25)
        r = smart.searchScrip("NSE", sym)
        if not r or not r.get('data'): return None
        token = r['data'][0]['symboltoken']
        today = ist_now().strftime("%Y-%m-%d")
        from_date = f"{today} 09:00"
        to_date = f"{today} 15:30"
        hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_date,"todate":to_date})
        if not hist or not hist.get('data') or len(hist['data']) < 30:
            from_date = (ist_now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:00")
            hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_date,"todate":to_date})
            if not hist or not hist.get('data') or len(hist['data']) < 30: return None

        df = pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)

        # Indicators
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['EMA15'] = df['Close'].ewm(span=15).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        df['AvgVol'] = df['Volume'].rolling(20).mean()
        df['RSI'] = calc_rsi(df['Close'], 14)

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        ltp = float(curr['Close'])
        ema9 = float(curr['EMA9']); ema15 = float(curr['EMA15'])
        vwap
