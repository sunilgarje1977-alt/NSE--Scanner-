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
def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", json={"chat_id": TELE_CHAT, "text": m, "parse_mode":"Markdown"}, timeout=20)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())

# 388 UNIQUE - PVRINOX INCLUDED - 500 TARGET LIST
SYMBOLS = ["PVRINOX", "SIEMENS", "GSFC", "COALINDIA", "BHEL", "SAIL", "SUZLON", "IRFC", "RVNL", "IREDA", "NHPC", "BEL", "BDL", "HAL", "MAZDOCK", "OIL", "NMDC", "TATACHEM", "VOLTAS", "KEI", "FEDERALBNK", "BANKINDIA", "AUROPHARMA", "LUPIN", "BSOFT", "BHARATFORG", "SONACOMS", "POLYCAB", "COFORGE", "BSE", "PAYTM", "VMM", "360ONE", "AFFLE", "AMBER", "BEML", "KPITTECH", "TATAELXSI", "LTTS", "PRESTIGE", "JINDALSTEL", "KAYNES", "KFINTECH", "MASTEK", "MCX", "OLECTRA", "TRENT", "ZOMATO", "DELHIVERY", "MAPMYINDIA", "MTARTECH", "CYIENT", "LICI", "LODHA", "CDSL", "DLF", "INDIGO", "IRCTC", "MOTHERSON", "PERSISTENT", "RBLBANK", "TATAPOWER", "TITAN", "VEDL", "DIXON", "INDIAMART", "INTELLECT", "NETWEB", "ELECON", "IEX", "JWL", "TEXRAIL", "RAILTEL", "RITES", "VBL", "SOBHA", "BRIGADE", "CUB", "FORTIS", "KPIL", "ABB", "CUMMINSIND", "HINDZINC", "JSWENERGY", "MRF", "NCC", "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC", "LT", "KOTAKBANK", "AXISBANK", "BAJFINANCE", "ASIANPAINT", "MARUTI", "WIPRO", "HCLTECH", "SUNPHARMA", "ULTRACEMCO", "POWERGRID", "NTPC", "ONGC", "TATASTEEL", "HINDALCO", "ADANIENT", "ADANIPORTS", "GRASIM", "CIPLA", "DRREDDY", "DIVISLAB", "BAJAJFINSV", "BAJAJ-AUTO", "EICHERMOT", "HEROMOTOCO", "M&M", "TATAMOTORS", "BRITANNIA", "NESTLEIND", "HINDUNILVR", "APOLLOHOSP", "UPL", "SHREECEM", "SBILIFE", "HDFCLIFE", "ICICIPRULI", "ICICIGI", "GODREJCP", "DABUR", "MARICO", "COLPAL", "PIDILITUP", "BERGEPAINT", "INDUSINDBK", "BANDHANBNK", "IDFCFIRSTB", "PNB", "CANBK", "UNIONBANK", "INDIANB", "AUBANK", "YESBANK", "MUTHOOTFIN", "MANAPPURAM", "CHOLAFIN", "SHRIRAMFIN", "PFC", "RECLTD", "CONCOR", "GMRINFRA", "ADANIGREEN", "ADANIPOWER", "SJVN", "NLCINDIA", "JSL", "APLAPOLLO", "WELCORP", "RATNAMANI", "ASTRAL", "FINCABLES", "RRKABEL", "HAVELLS", "CROMPTON", "BLUESTARCO", "WHIRLPOOL", "PGEL", "SYRMA", "CENTUM", "AVALON", "IKIO", "DEEPAKNTR", "AARTIIND", "ATUL", "NAVINFLUOR", "SRF", "PIIND", "COROMANDEL", "CHAMBLFERT", "GNFC", "FACT", "RCF", "BALRAMCHIN", "TRIVENI", "RENUKA", "EIDPARRY", "COCHINSHIP", "GRSE", "MIDHANI", "PRAJIND", "ISGEC", "THERMAX", "HONAUT", "SCHNEIDER", "KEC", "KALPATPOWR", "L&T", "IRB", "DBL", "PNCINFRA", "GRINFRA", "HGINFRA", "KNRCON", "ASHOKA", "GODREJPROP", "OBEROIRLTY", "PHOENIXLTD", "IBREALEST", "ANANTRAJ", "NBCC", "HUDCO", "INDIACEM", "JKCEMENT", "RAMCOCEM", "ACC", "AMBUJACEM", "DALBHARAT", "ORIENTCEM", "HEIDELBERG", "NUVOCO", "RAJESHEXPO", "KALYANKJIL", "SENCO", "PCJEWELLER", "MOTILALOFS", "ANGELONE", "CAMS", "NUVAMA", "UTIAMC", "HDFCAMC", "NAM-INDIA", "STARHEALTH", "GICRE", "NIACL", "SBICARD", "TATACOMM", "IDEA", "TEJASNET", "ITI", "HFCL", "STERLITE", "JUSTDIAL", "MPHASIS", "ZENSAR", "TATATECH", "TATACONSUM", "VSTIND", "GODFREY", "RADICO", "SOMANY", "CERA", "KAJARIACER", "HSIL", "TTKPRESTIG", "BATAINDIA", "RELAXO", "METROBRAND", "CAMPUS", "LIBERTY", "MAYURUNIQ", "WELSPUNLIV", "TRIDENT", "RAYMOND", "ARVIND", "PAGEIND", "LUXIND", "KPRMILL", "SWANENERGY", "ABFRL", "DMART", "V2RETAIL", "LALPATHLAB", "METROPOLIS", "MAXHEALTH", "MEDANTA", "ASTERDM", "KIMS", "POLYMED", "SYNGENE", "LAURUSLABS", "GRANULES", "ZYDUSLIFE", "IPCALAB", "ALKEM", "TORNTPHARM", "JBCHEPHARM", "ERIS", "AJANTPHARM", "NATCOPHARM", "CAPLIPOINT", "GLAND", "WOCKPHARMA", "GLAXO", "PFIZER", "SANOFI", "ABBOTT", "HIKAL", "ADANITRANS", "CESC", "TORNTPOWER", "SUNTV", "ZEEL", "SAREGAMA", "TIPSINDLTD", "NAZARA", "SWIGGY", "NYKAA", "EASEMYTRIP", "SPICEJET"]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).ewm(alpha=1/p).mean(); l=(-d.where(d<0,0)).ewm(alpha=1/p).mean()
    return 100 - (100/(1+g/l))

def analyze(sym):
    try:
        r=smart.searchScrip("NSE", sym)
        if not r or not r.get('data'): return None
        token=r['data'][0]['symboltoken']
        today=ist_now().strftime("%Y-%m-%d")
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:00","todate":f"{today} 15:30"})
        if not hist or not hist.get('data') or len(hist['data'])<20: return None
        df=pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)
        df['EMA9']=df['Close'].ewm(span=9).mean()
        df['EMA15']=df['Close'].ewm(span=15).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3*df['Volume']).cumsum()/df['Volume'].cumsum()
        df['RSI']=calc_rsi(df['Close'])
        c=df.iloc[-1]; p=df.iloc[-2] # ON-TIME - फक्त आत्ताचा
        if c['Close']<30: return None
        try: ts=str(c['Time']).split('T')[1][:5]
        except: ts=""
        if p['Close'] <= p['VWAP'] and c['Close'] > c['VWAP'] and c['EMA9']>c['EMA15'] and c['RSI']>=50:
            return f"🟢 BUY {sym} @ {c['Close']:.1f} [{ts}] VWAP CROSS | RSI{int(c['RSI'])}"
        if p['Close'] >= p['VWAP'] and c['Close'] < c['VWAP'] and c['EMA9']<c['EMA15'] and c['RSI']<=50:
            return f"🔴 SELL {sym} @ {c['Close']:.1f} [{ts}] VWAP DOWN | RSI{int(c['RSI'])}"
        return None
    except: return None

results=[]
with ThreadPoolExecutor(max_workers=25) as ex:
    fut={ex.submit(analyze,s):s for s in SYMBOLS}
    for f in as_completed(fut):
        r=f.result()
        if r: results.append(r)

now_str=ist_now().strftime("%d-%b %H:%M")
msg = f"✅ *BSE {len(SYMBOLS)} {now_str}*\n\n" + "\n".join(sorted(results)[:50]) if results else f"📊 BSE {len(SYMBOLS)} {now_str}\nNo Fresh Cross - Active ✅"
send_tg(msg)
print(msg)
