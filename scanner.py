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
    try: requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", json={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())

SYMBOLS = ["PGEL","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","NMDC","NATIONALUM","TATACHEM","ASHOKLEY","VOLTAS","BLUESTARCO","MARICO","UBL","MCDOWELL-N","RADICO","PATANJALI","APARINDS","KEI","FEDERALBNK","BANKINDIA","INDIANB","MAHABANK","IDBI","AUROPHARMA","LUPIN","GLENMARK","BIOCON","AARTIIND","ALKEM","BALKRISIND","BSOFT","CUMMINSIND","ESCORTS","EXIDEIND","INDHOTEL","SUPREMEIND","BHARATFORG","UNOMINDA","TORNTPOWER","SONACOMS","POLYCAB","HDFCAMC","COFORGE","BSE","MUTHOOTFIN","PAYTM","VMM","WAAREENER","360ONE","AAVAS","ACE","AFFLE","AMBER","ANGELONE","BEML","BLS","BLUEDART","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","IRB","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KAYNES","KEC","KFINTECH","M&MFIN","MANAPPURAM","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OBEROIRLTY","OLECTRA","PEL","PIIND","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","LICI","LODHA","LTF","AUBANK","ADANIGREEN","ADANIPOWER","BANKBARODA","BANDHANBNK","BATAINDIA","CANBK","CDSL","CGPOWER","CHOLAFIN","DABUR","DLF","DMART","GAIL","GODREJCP","GODREJPROP","HAVELLS","IDFCFIRSTB","INDIGO","IOC","IRCTC","LALPATHLAB","LAURUSLABS","LTIM","MOTHERSON","MPHASIS","NAM-INDIA","OFSS","PAGEIND","PERSISTENT","PNB","PVRINOX","RBLBANK","SRF","TATACOMM","TATAPOWER","TITAN","UBL","VEDL","DIXON","KAJARIACER","SAFARI","CAMPUS","METROBRAND","RELAXO","BOROSIL","GREENPANEL","CENTURYPLY","INDIAMART","INTELLECT","NETWEB","SYRMA","AVALON","CYIENTDLM","DATAPATTNS","PARAS","TATATECH","ELECON","HFCL","IEX","JWL","TEXRAIL","RAILTEL","RITES","CESC","MGL","WAAREERTL","KPIGREEN","VARUNBEV","VBL","DEVYANI","CHALET","EASEMYTRIP","BLS","TBO","V2RETAIL","VMART","ABFRL","RAYMOND","WELSPUNLIV","SOBHA","BRIGADE","ANANTRAJ","JPOWER","KARURVYSYA","CUB","UJJIVAN","EQUITAS","CAPLIPOINT","FORTIS","KIMS","SULA","GODFRYPHLP"]

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
        if len(df) < 20: return None
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)
        curr = df.iloc[-1]
        ltp = float(curr['Close'])
        vol = float(curr['Volume'])
        if ltp < 50: return None
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        ema9 = float(curr['EMA9']); vwap = float(curr['VWAP'])
        pct_vwap = (ltp/vwap-1)*100
        # Score काढ - जेवढा वर तेवढा चांगला
        return (pct_vwap, ltp, vol, ema9, vwap, sym)
    except:
        return None

all_data=[]
with ThreadPoolExecutor(max_workers=20) as ex:
    futures = {ex.submit(analyze, s): s for s in set(SYMBOLS)}
    for f in as_completed(futures):
        r=f.result()
        if r: all_data.append(r)

# Sort VWAP % ने
all_data = sorted(all_data, key=lambda x: x[0], reverse=True)
now_str = ist_now().strftime("%d-%b %H:%M")

if not all_data:
    send_tg(f"{now_str} - Data नाही आला")
else:
    # BUY List - VWAP वर असलेले
    buys = [x for x in all_data if x[0] > 0 and x[1] > x[3]]

    if buys:
        txt = "\n".join([f"🟢 {x[5]} @ {x[1]:.1f} VWAP+{x[0]:.2f}% Vol {int(x[2]/1000)}k" for x in buys[:20]])
        msg = f"🚀 *SmallCap BUY {now_str}*\n{len(all_data)} checked\n\n{txt}"
    else:
        # दुपारी सगळे VWAP खाली असतील तर Top 15 जवळचे दाखव - NO TRADE नको
        txt = "\n".join([f"⚪ {x[5]} @ {x[1]:.1f} VWAP {x[0]:.2f}% (WAIT)" for x in all_data[:15]])
        msg = f"⏳ *Market Down - Top Near VWAP {now_str}*\n{len(all_data)} checked - सगळे VWAP खाली\n\n{txt}\n\nसकाळी 10 वा परत पळतील"

    send_tg(msg)
    print(msg)
