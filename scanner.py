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
def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage",
                      json={"chat_id": TELE_CHAT, "text": m, "parse_mode":"Markdown"}, timeout=25)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())

# 500 SHARE LIST - PVRINOX INCLUDED
SYMBOLS = ["PVRINOX","SIEMENS","GSFC","COALINDIA","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","BEL","BDL","HAL","MAZDOCK","OIL","NMDC","TATACHEM","VOLTAS","KEI","FEDERALBNK","BANKINDIA","AUROPHARMA","LUPIN","BSOFT","BHARATFORG","SONACOMS","POLYCAB","COFORGE","BSE","PAYTM","VMM","360ONE","AFFLE","AMBER","BEML","KPITTECH","TATAELXSI","LTTS","PRESTIGE","JINDALSTEL","KAYNES","KFINTECH","MASTEK","MCX","OLECTRA","TRENT","ZOMATO","DELHIVERY","MAPMYINDIA","MTARTECH","CYIENT","LICI","LODHA","BANKBARODA","CDSL","DLF","INDIGO","IRCTC","MOTHERSON","PERSISTENT","RBLBANK","TATAPOWER","TITAN","VEDL","DIXON","INDIAMART","INTELLECT","NETWEB","ELECON","IEX","JWL","TEXRAIL","RAILTEL","RITES","VBL","SOBHA","BRIGADE","CUB","FORTIS","KPIL","ABB","CUMMINSIND","HINDZINC","JSWENERGY","MRF","NCC","RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","AXISBANK","BAJFINANCE","ASIANPAINT","MARUTI","WIPRO","HCLTECH","SUNPHARMA","ULTRACEMCO","TITAN","POWERGRID","NTPC","ONGC","TATASTEEL","JSWSTEEL","HINDALCO","ADANIENT","ADANIPORTS","GRASIM","CIPLA","DRREDDY","DIVISLAB","BAJAJFINSV","BAJAJ-AUTO","EICHERMOT","HEROMOTOCO","M&M","TATAMOTORS","BRITANNIA","NESTLEIND","HINDUNILVR","APOLLOHOSP","UPL","SHREECEM","SBILIFE","HDFCLIFE","ICICIPRULI","ICICIGI","BAJAJHLDNG","GODREJCP","DABUR","MARICO","COLPAL","PIDILITUP","BERGEPAINT","INDUSINDBK","BANDHANBNK","IDFCFIRSTB","PNB","CANBK","UNIONBANK","INDIANB","AUBANK","YESBANK","MUTHOOTFIN","MANAPPURAM","CHOLAFIN","SHRIRAMFIN","PFC","RECLTD","IRCTC","CONCOR","GMRINFRA","ADANIGREEN","ADANIPOWER","TATAPOWER","JSWENERGY","NHPC","SJVN","NLCINDIA","COALINDIA","HINDZINC","VEDL","NMDC","SAIL","JINDALSTEL","TATASTEEL","JSL","JSLHISAR","APLAPOLLO","WELCORP","RATNAMANI","ASTRAL","POLYCAB","KEI","FINCABLES","RRKABEL","HAVELLS","CROMPTON","VOLTAS","BLUESTARCO","WHIRLPOOL","DIXON","AMBER","KAYNES","SYRMA","CENTUM","AVALON","IKIO","PGEL","TATACHEM","DEEPAKNTR","AARTIIND","ATUL","NAVINFLUOR","SRF","PIIND","UPL","COROMANDEL","CHAMBLFERT","GNFC","GSFC","FACT","RCF","TATACHEM","BALRAMCHIN","TRIVENI","RENUKA","EIDPARRY","SAIL","BHEL","BEML","BDL","BEL","HAL","MAZDOCK","COCHINSHIP","GRSE","MIDHANI","PRAJIND","ISGEC","THERMAX","CUMMINSIND","ABB","SIEMENS","SCHNEIDER","HONAUT","VOLTAS","KEC","KALPATPOWR","KPIL","LTTS","L&T","NCC","IRB","GMRINFRA","DBL","PNCINFRA","GRINFRA","HGINFRA","KNRCON","ASHOKA","SOBHA","PRESTIGE","BRIGADE","LODHA","DLF","GODREJPROP","OBEROIRLTY","PHOENIXLTD","IBREALEST","ANANTRAJ","NBCC","HUDCO","INDIACEM","JKCEMENT","RAMCOCEM","SHREECEM","ULTRACEMCO","ACC","AMBUJACEM","DALBHARAT","JKLC","ORIENTCEM","HEIDELBERG","NUVOCO","VOLTAS","RAJESHEXPO","TITAN","KALYANKJIL","SENCO","TBZ","THANGAMAYL","PCJEWELLER","MOTILALOFS","ANGELONE","BSE","CDSL","MCX","NUVAMA","KFINTECH","CAMS","UTIAMC","HDFCAMC","NAM-INDIA","ICICIGI","SBILIFE","HDFCLIFE","LICI","STARHEALTH","GICRE","NIACL","NEWINDIA","SBICARD","PFC","RECLTD","IEX","TATAPOWER","ADANITRANS","POWERGRID","TORNTPOWER","CESC","JSWENERGY","TATAPOWER","PVRINOX","SUNTV","ZEEL","SAREGAMA","TIPSINDLTD","NAZARA","ZOMATO","SWIGGY","PAYTM","NYKAA","DELHIVERY","EASEMYTRIP","IRCTC","INDIGO","SPICEJET","TATACOMM","BHARTIARTL","IDEA","TEJASNET","ITI","HFCL","STERLITE","INDIAMART","JUSTDIAL","INTELLECT","BSOFT","COFORGE","PERSISTENT","MPHASIS","LTTS","TATAELXSI","KPITTECH","CYIENT","ZENSAR","MASTEK","SONACOMS","TATATECH","TATACONSUM","VBL","TATACONSUM","NESTLEIND","BRITANNIA","MARICO","DABUR","GODREJCP","COLPAL","HINDUNILVR","ITC","VSTIND","GODFREY","RADICO","SOMANY","CERA","KAJARIACER","HSIL","LAOPALA","TTKPRESTIG","BATAINDIA","RELAXO","METROBRAND","CAMPUS","LIBERTY","MAYURUNIQ","WELSPUNLIV","TRIDENT","ALOKINDS","RAYMOND","ARVIND","PAGEIND","LUXIND","DOLLAR","GOKEX","KPRMILL","GARFIBRES","SWANENERGY","ABFRL","TRENT","DMART","V2RETAIL","VMM","360ONE","AFFLE","KPITTECH","LALPATHLAB","METROPOLIS","DRREDDY","APOLLOHOSP","FORTIS","MAXHEALTH","NARAYANHrudayalaya","MEDANTA","ASTERDM","RAINBOW","KIMS","STARHEALTH","POLYMED","NARAYANA","SYNGENE","DIVISLAB","LAURUSLABS","GRANULES","AUROPHARMA","LUPIN","CIPLA","SUNPHARMA","ZYDUSLIFE","IPCALAB","ALKEM","TORNTPHARM","ABBOTT","PFIZER","SANOFI","GLAXO","JBCHEPHARM","ERIS","AJANTPHARM","NATCOPHARM","MARKANS","CAPLIPOINT","HIKAL","ASTRAZEN","GLAND","WOCKPHARMA"]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).ewm(alpha=1/p).mean(); l=(-d.where(d<0,0)).ewm(alpha=1/p).mean()
    return 100 - (100/(1+g/l))

def analyze(sym):
    try:
        time.sleep(0.02)
        r=smart.searchScrip("NSE", sym)
        if not r or not r.get('data'): return None
        token=r['data'][0]['symboltoken']
        today=ist_now().strftime("%Y-%m-%d")
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:00","todate":f"{today} 15:30"})
        if not hist or not hist.get('data') or len(hist['data'])<25: return None
        df=pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)
        df['EMA9']=df['Close'].ewm(span=9).mean()
        df['EMA15']=df['Close'].ewm(span=15).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3*df['Volume']).cumsum()/df['Volume'].cumsum()
        df['RSI']=calc_rsi(df['Close'])
        # 90 min lookback = PVRINOX सारखा मोठा Move पण Catch होईल
        for idx in range(len(df)-1, max(len(df)-19, 0), -1):
            c=df.iloc[idx]; p=df.iloc[idx-1]
            if c['Close']<30: continue
            try: ts=str(c['Time']).split('T')[1][:5]
            except: ts=""
            vol_ok = c['Volume'] > 0
            if p['Close'] <= p['VWAP'] and c['Close'] > c['VWAP'] and c['EMA9']>c['EMA15'] and c['Close']>c['Open'] and c['RSI']>=52 and vol_ok:
                return f"🟢 BUY {sym} @ {c['Close']:.1f} [{ts}] VWAP+EMA | RSI{int(c['RSI'])} | VOL{c['Volume']/1000:.0f}K"
            if p['Close'] >= p['VWAP'] and c['Close'] < c['VWAP'] and c['EMA9']<c['EMA15'] and c['Open']>c['Close'] and c['RSI']<=50:
                return f"🔴 SELL {sym} @ {c['Close']:.1f} [{ts}] VWAP-DOWN | RSI{int(c['RSI'])}"
        return None
    except: return None

results=[]
with ThreadPoolExecutor(max_workers=20) as ex:
    fut={ex.submit(analyze,s):s for s in set(SYMBOLS)}
    for f in as_completed(fut):
        r=f.result()
        if r: results.append(r)

now_str=ist_now().strftime("%d-%b %H:%M")
if results:
    msg=f"✅ *BSE {len(set(SYMBOLS))} {now_str}*\n\n" + "\n".join(sorted(results)[:40])
else:
    msg=f"📊 BSE {len(set(SYMBOLS))} {now_str}\nNo Fresh Cross - Active ✅"
send_tg(msg)
print(msg)
