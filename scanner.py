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
    try: requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", json={"chat_id": TELE_CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

SYMBOLS = ["PGEL","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","SJVN","HUDCO","IRCON","NBCC","NCC","BEL","BDL","HAL","MAZDOCK","COCHINSHIP","GRSE","OIL","NMDC","TATACHEM","ASHOKLEY","VOLTAS","BLUESTARCO","MARICO","UBL","MCDOWELL-N","RADICO","PATANJALI","APARINDS","KEI","FEDERALBNK","BANKINDIA","INDIANB","MAHABANK","IDBI","AUROPHARMA","LUPIN","GLENMARK","BIOCON","AARTIIND","ALKEM","BALKRISIND","BSOFT","CUMMINSIND","ESCORTS","EXIDEIND","INDHOTEL","SUPREMEIND","BHARATFORG","UNOMINDA","TORNTPOWER","SONACOMS","POLYCAB","HDFCAMC","COFORGE","BSE","MUTHOOTFIN","PAYTM","VMM","WAAREENER","360ONE","AAVAS","ACE","AFFLE","AMBER","ANGELONE","BEML","BLS","BLUEDART","KPITTECH","TATAELXSI","LTTS","CONCOR","PRESTIGE","PHOENIXLTD","SBICARD","IRB","JINDALSTEL","JSL","JSWENERGY","JUBLFOOD","KALYANKJIL","KAYNES","KEC","KFINTECH","M&MFIN","MANAPPURAM","MASTEK","MCX","MEDANTA","NATCOPHARM","NAUKRI","OBEROIRLTY","OLECTRA","PEL","PIIND","PNBHOUSING","RECLTD","SIEMENS","SUNTV","SYNGENE","TRENT","TRIDENT","ZYDUSLIFE","ZOMATO","DELHIVERY","MAPMYINDIA","PNCINFRA","GRINFRA","MTARTECH","CYIENT","TANLA","ROUTE","HAPPSTMNDS","LICI","LODHA","LTF","AUBANK","ADANIGREEN","ADANIPOWER","BANKBARODA","BANDHANBNK","BATAINDIA","CANBK","CDSL","CGPOWER","CHOLAFIN","DABUR","DLF","DMART","GAIL","GODREJCP","GODREJPROP","HAVELLS","IDFCFIRSTB","INDIGO","IOC","IRCTC","LALPATHLAB","LAURUSLABS","LTIM","MOTHERSON","MPHASIS","OFSS","PAGEIND","PERSISTENT","PNB","PVRINOX","RBLBANK","SRF","TATACOMM","TATAPOWER","TITAN","UBL","VEDL","DIXON","SAFARI","CAMPUS","METROBRAND","BOROSIL","GREENPANEL","INDIAMART","INTELLECT","NETWEB","SYRMA","AVALON","DATAPATTNS","PARAS","TATATECH","ELECON","HFCL","IEX","JWL","TEXRAIL","RAILTEL","RITES","CESC","MGL","WAAREERTL","VARUNBEV","VBL","DEVYANI","CHALET","EASEMYTRIP","BLS","V2RETAIL","VMART","ABFRL","RAYMOND","WELSPUNLIV","SOBHA","BRIGADE","ANANTRAJ","JPOWER","KARURVYSYA","CUB","UJJIVAN","EQUITAS","FORTIS","KIMS","SULA","GODFRYPHLP"]

def analyze(sym):
    try:
        time.sleep(0.3) # API Block होऊ नये म्हणून
        r = smart.searchScrip("NSE", sym)
        if not r or not r.get('data'): return None
        token = r['data'][0]['symboltoken']
        # फक्त आजचा Data घे - 3 दिवस नको
        today = ist_now().strftime("%Y-%m-%d")
        from_date = f"{today} 09:00"
        to_date = f"{today} 15:30"
        hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_date,"todate":to_date})
        if not hist or not hist.get('data') or len(hist['data']) < 10:
            # जर आजचा नाही भेटला तर 1 दिवस मागचा घे
            from_date = (ist_now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d 09:00")
            hist = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_date,"todate":to_date})
            if not hist or not hist.get('data'): return None

        df = pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)
        curr = df.iloc[-1]
        ltp = float(curr['Close']); vol = float(curr['Volume'])
        if ltp < 50: return None
        df['EMA9'] = df['Close'].ewm(span=9).mean()
        df['VWAP'] = ((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        ema9 = float(curr['EMA9']); vwap = float(curr['VWAP'])
        pct = (ltp/vwap-1)*100
        return (pct, ltp, vol, ema9, vwap, sym)
    except Exception as e:
        print(f"{sym} error {e}")
        return None

all_data=[]
# Worker 5 केले - Block होणार नाही
with ThreadPoolExecutor(max_workers=5) as ex:
    futures = {ex.submit(analyze, s): s for s in set(SYMBOLS)}
    for f in as_completed(futures):
        r=f.result()
        if r: all_data.append(r)

all_data = sorted(all_data, key=lambda x: x[0], reverse=True)
now_str = ist_now().strftime("%d-%b %H:%M")

if not all_data:
    msg = f"{now_str} - Data नाही आला (API Limit) - 5 मिनिटाने परत Run करा"
else:
    buys = [x for x in all_data if x[0] > 0]
    if buys:
        txt = "\n".join([f"🟢 {x[5]} @ {x[1]:.1f} VWAP+{x[0]:.2f}% Vol {int(x[2]/1000)}k" for x in buys[:20]])
        msg = f"🚀 *SmallCap 50+ {now_str}*\n{len(all_data)} stocks OK\n\n{txt}"
    else:
        txt = "\n".join([f"⚪ {x[5]} @ {x[1]:.1f} {x[0]:.2f}%" for x in all_data[:15]])
        msg = f"⏳ *All Below VWAP {now_str}*\n{len(all_data)} checked\n\n{txt}"

send_tg(msg)
print(msg) 
