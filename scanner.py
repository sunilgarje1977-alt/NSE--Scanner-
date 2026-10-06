import os, datetime, pytz, requests, pyotp, time
import pandas as pd
from SmartApi import SmartConnect
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Secrets ---
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
        for i in range(0, len(m), 3500):
            requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage",
                          json={"chat_id": TELE_CHAT, "text": m[i:i+3500], "parse_mode":"Markdown"}, timeout=20)
            time.sleep(1)
    except Exception as e:
        print(f"TG Error {e}")

# --- Angel Login ---
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())

# --- BSE 1000 LIST ---
BSE1000 = [
"RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","SBIN","BHARTIARTL","LICI","ITC","HINDUNILVR","LT","BAJFINANCE","KOTAKBANK","HCLTECH","AXISBANK","ASIANPAINT","MARUTI","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","ONGC","NTPC","POWERGRID","M&M","TATAMOTORS","TATASTEEL","ADANIENT","ADANIPORTS","JSWSTEEL","BAJAJFINSV","GRASIM","TECHM","HINDALCO","CIPLA","DIVISLAB","DRREDDY","APOLLOHOSP","BRITANNIA","EICHERMOT","HEROMOTOCO","BPCL","COALINDIA","SBILIFE","HDFCLIFE","BAJAJ-AUTO","NESTLEIND","TATACONSUM","UPL","TATAPOWER",
"ABB","ACC","AUBANK","AARTIIND","ABBOTINDIA","ADANIGREEN","ADANIPOWER","ABCAPITAL","ABFRL","MCDOWELL-N","AMBUJACEM","APOLLOTYRE","ASHOKLEY","AUROPHARMA","DMART","BAJAJHLDNG","BANKBARODA","BATAINDIA","BEL","BEML","BHARATFORG","BHEL","BIOCON","BOSCHLTD","BSOFT","CESC","CGPOWER","CANBK","CHOLAFIN","CUMMINSIND","DLF","FEDERALBNK","GODREJCP","GODREJPROP","HAVELLS","HINDPETRO","ICICIGI","ICICIPRULI","IDFCFIRSTB","INDIGO","IOC","IRCTC","JINDALSTEL","JSWENERGY","JUBLFOOD","LUPIN","MRF","MOTHERSON","MPHASIS","NHPC","NMDC","OIL","PAGEIND","PERSISTENT","PETRONET","PIDILITIND","PEL","PNB","RECLTD","SAIL","SIEMENS","TORNTPHARM","TRENT","VEDL","VOLTAS","ZEEL","ZYDUSLIFE","GAIL","CONCOR","ICICIGI","DLF","INDUSINDBK",
"360ONE","AFFLE","AMBER","ANGELONE","ANANTRAJ","APARINDS","APTUS","ATGL","BSE","BLS","BLUESTARCO","CAMPUS","CDSL","CAMS","CANFINHOME","CARTRADE","CEATLTD","CENTURYTEX","CHALET","CUB","CRAFTSMAN","CREDITACC","CYIENT","DEEPAKNTR","DELHIVERY","DIXON","ELECON","ELGIEQUIP","EMUDHRA","FSL","FORTIS","GLENMARK","GRINDWELL","GSFC","GSPL","HAPPSTMNDS","HFCL","HONASA","IEX","IIFL","INDIAMART","INDIANB","INTELLECT","IRB","JBMA","JWL","JSL","KARURVYSYA","KAYNES","KEC","KEI","KFINTECH","KPITTECH","LTTS","LATENTVIEW","LAURUSLABS","LODHA","MEDANTA","METROPOLIS","MFSL","MTARTECH","MUTHOOTFIN","NCC","NATIONALUM","NAUKRI","NETWEB","OBEROIRLTY","OLECTRA","PAYTM","PNCINFRA","POLYCAB","POONAWALLA","PRESTIGE","RBLBANK","RAILTEL","RITES","ROUTE","SAFARI","SONACOMS","SOBHA","BRIGADE","SUNDRMFAST","SUNTV","TANLA","TATAELXSI","TATACHEM","TATACOMM","TEXRAIL","TIMKEN","TRIVENI","TRIDENT","TVSMOTOR","VBL","VMM","VMART","VGUARD","WAAREENER","WELCORP","ZOMATO","CDSL","MCX","BDL","HAL","MAZDOCK","RVNL","IRFC","IREDA","SUZLON","NHPC","OIL","BEL","BHEL",
"ACE","AETHER","AHLUCONT","AIAENG","AJANTPHARM","AKZOINDIA","ALEMBICLTD","ALKYLAMINE","ALOKINDS","ANANDRATHI","ANURAS","APLLTD","ARVIND","ASTERDM","ASTRAL","ATUL","AVANTIFEED","BALKRISIND","BALRAMCHIN","BANDHANBNK","BAYERCROP","BDL","BIKAJI","BIRLACORPN","BLUEDART","BORORENEW","CARBORUNDU","CASTROLIND","CERA","CHAMBLFERT","CHEMPLASTS","CIEINDIA","COFORGE","COLPAL","CRISIL","CROMPTON","CSBBANK","DATAPATTNS","DCBBANK","DCMSHRIRAM","DEVYANI","DHANUKA","DBL","EIDPARRY","EIHOTEL","EMAMILTD","ENDURANCE","EQUITASBNK","ERIS","ESABINDIA","EXIDEIND","FDC","FINEORG","FINCABLES","GAIL","GALAXYSURF","GARFIBRES","GLAXO","GMDCLTD","GNFC","GODFRYPHLP","GODREJIND","GRANULES","GRAPHITE","GRSE","GESHIP","HAL","HATHWAY","HATSUN","HERITGFOOD","HIKAL","HLEGLAS","HONAUT","HUDCO","ICRA","IDBI","IDFC","IIFLSEC","INDIACEM","INDIGOPNTS","INDOCO","INFIBEAM","INGERRAND","INOXWIND","IOLCP","IPCALAB","IRCON","ITI","J&KBANK","JBCHEPHARM","JINDALSAW","JKLAKSHMI","JKCEMENT","JKPAPER","JKTYRE","JMFINANCIL","JUBLINGREA","JUBLPHARMA","JUSTDIAL","JYOTHYLAB","KAJARIACER","KALYANKJIL","KANSAINER","KNRCON","KRBL","KSB","KSCL","KTKBANK","LALPATHLAB","LAXMIMACH","LEMONTREE","LICHSGFIN","LINDEINDIA","LUXIND","MAHABANK","MAHLIFE","MAHLOG","MANAPPURAM","MANINFRA","MANYAVAR","MAPMYINDIA","MASTEK","MAXHEALTH","MAZDOCK","MGL","MHRIL","MIDHANI","MINDACORP","MOIL","MOTILALOFS","MRPL","NATCOPHARM","NAVINFLUOR","NBCC","NCC","NEOGEN","NESCO","NH","NLCINDIA","NOCIL","OFSS","ORIENTELEC","PCBL","PFIZER","PHOENIXLTD","PNBHOUSING","POLYMED","PRAJIND","PRINCEPIPE","PRSMJOHNSN","PSB","PTC","PVRINOX","QUESS","RADICO","RAJESHEXPO","RALLIS","RAMCOCEM","RATNAMANI","RAYMOND","REDINGTON","RELAXO","RHIM","SAPPHIRE","SAREGAMA","SBFC","SCHAEFFLER","SCI","SEQUENT","SFL","SHOPERSTOP","SOUTHBANK","SPARC","STLTECH","SUDARSCHEM","SUMICHEM","SUPREMEIND","SWANENERGY","SYMPHONY","SYNGENE","TATAMETALI","TCI","TCIEXP","TEAMLEASE","THERMAX","THOMASCOOK","TIINDIA","TITAGARH","TORNTPOWER","TRITURBINE","TTKPRESTIG","TV18BRDCST","UBL","UCOBANK","UJJIVANSFB","UNIONBANK","UNOMINDA","VTL","VARROC","VIJAYA","VINATIORGA","VIPIND","VRLLOG","WELSPUNLIV","WESTLIFE","WHIRLPOOL","ZENSARTECH","ZYDUSWELL","PGEL","KPIL","KAYNES","ABB","CUMMINSIND","HINDZINC","JSWENERGY","MRF","NCC","RVNL","KPIL"
]
SYMBOLS = list(dict.fromkeys(BSE1000)) # duplicate remove

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).ewm(alpha=1/p).mean(); l=(-d.where(d<0,0)).ewm(alpha=1/p).mean()
    rs=g/l; return 100 - (100/(1+rs))

def analyze(sym):
    try:
        # === 9:15 ते 3:15 वेळ चेक ===
        now = ist_now()
        now_min = now.hour*60 + now.minute
        if now_min < 555 or now_min > 915: # 9:15=555, 15:15=915
            return None

        time.sleep(0.08)
        r=smart.searchScrip("NSE", sym)
        if not r or not r.get('data'): return None
        token=r['data'][0]['symboltoken']
        today=now.strftime("%Y-%m-%d")
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:00","todate":f"{today} 15:30"})
        if not hist or not hist.get('data') or len(hist['data'])<35: return None

        df=pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)
        df['EMA9']=df['Close'].ewm(span=9).mean()
        df['EMA15']=df['Close'].ewm(span=15).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3*df['Volume']).cumsum()/df['Volume'].cumsum()
        df['AvgVol']=df['Volume'].rolling(20).mean()
        df['RSI']=calc_rsi(df['Close'])

        # शेवटच्या 24 candle (120 मिनिट) मध्ये नवीन Signal शोध
        for idx in range(len(df)-1, max(len(df)-25, 0), -1):
            c=df.iloc[idx]; p=df.iloc[idx-1]
            ltp=c['Close']; op=c['Open']; hi=c['High']; lo=c['Low']
            rng=hi-lo
            if rng==0 or ltp<20: continue
            body_pct=abs(ltp-op)/rng
            big_green = ltp>op and body_pct>=0.45
            big_red = op>ltp and body_pct>=0.45
            vol_ok = c['Volume'] > c['AvgVol']*1.15
            try: time_str=str(c['Time']).split('T')[1][:5]
            except: time_str=""

            # 🟢 BUY - GSFC/SIEMENS Pattern - VWAP UP Cross
            buy_cross = p['Close'] <= p['VWAP'] and ltp > c['VWAP']
            buy_ema = c['EMA9'] > c['VWAP'] and c['EMA15'] > c['VWAP'] and c['EMA9'] > c['EMA15']
            if buy_cross and buy_ema and big_green and vol_ok and 55 <= c['RSI'] <= 80:
                return f"🟢 BUY {sym} @ {ltp:.1f} [{time_str}] VWAP UP 9>15 RSI{c['RSI']:.0f} Vol{c['Volume']/c['AvgVol']:.1f}x Green{body_pct*100:.0f}%"

            # 🔴 SELL - COALINDIA Pattern - VWAP DOWN Cross
            sell_cross = p['Close'] >= p['VWAP'] and ltp < c['VWAP']
            sell_ema = c['EMA9'] < c['VWAP'] and c['EMA15'] < c['VWAP'] and c['EMA9'] < c['EMA15']
            if sell_cross and sell_ema and big_red and vol_ok and 20 <= c['RSI'] <= 48:
                return f"🔴 SELL {sym} @ {ltp:.1f} [{time_str}] VWAP DOWN 9<15 RSI{c['RSI']:.0f} Vol{c['Volume']/c['AvgVol']:.1f}x Red{body_pct*100:.0f}%"

        return None
    except:
        return None

# --- Scan BSE 1000 ---
results=[]
with ThreadPoolExecutor(max_workers=10) as ex:
    fut={ex.submit(analyze,s):s for s in set(SYMBOLS)}
    for f in as_completed(fut):
        r=f.result()
        if r: results.append(r)

now=ist_now().strftime("%d-%b %H:%M")
def get_time(x):
    try: return x.split('[')[1].split(']')[0]
    except: return "00:00"
results_sorted=sorted(results, key=lambda x: get_time(x), reverse=True)

if results_sorted:
    buys=[x for x in results_sorted if "BUY" in x]
    sells=[x for x in results_sorted if "SELL" in x]
    msg=f"✅ *BSE {len(set(SYMBOLS))} On-Time VWAP 9/15 Scanner {now}*\n09:15-15:15 Live\n\n"
    if buys: msg+= f"*🟢 BUY ({len(buys)}):*\n" + "\n".join(buys[:25]) + "\n\n"
    if sells: msg+= f"*🔴 SELL ({len(sells)}):*\n" + "\n".join(sells[:25])
else:
    # Market time check
    now_min = ist_now().hour*60 + ist_now().minute
    if now_min < 555 or now_min > 915:
        msg=f"⏰ Market Closed {now}\nScanner 9:15-15:15 चालतो"
    else:
        msg=f"📊 BSE {len(set(SYMBOLS))} Scanner {now}\n\n⏸️ No Fresh VWAP Big Candle Cross last 120min"

send_tg(msg)
print(msg)
