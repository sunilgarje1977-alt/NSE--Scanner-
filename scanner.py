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
                      json={"chat_id": TELE_CHAT, "text": m, "parse_mode":"Markdown"}, timeout=20)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())

# BSE 433 / 1000 - तुझा आहे तोच ठेव
SYMBOLS = ["SIEMENS","GSFC","COALINDIA","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","BEL","BDL","HAL","MAZDOCK","OIL","NMDC","TATACHEM","VOLTAS","KEI","FEDERALBNK","BANKINDIA","AUROPHARMA","LUPIN","BSOFT","BHARATFORG","SONACOMS","POLYCAB","COFORGE","BSE","PAYTM","VMM","360ONE","AFFLE","AMBER","BEML","KPITTECH","TATAELXSI","LTTS","PRESTIGE","JINDALSTEL","KAYNES","KFINTECH","MASTEK","MCX","OLECTRA","TRENT","ZOMATO","DELHIVERY","MAPMYINDIA","MTARTECH","CYIENT","LICI","LODHA","BANKBARODA","CDSL","DLF","INDIGO","IRCTC","MOTHERSON","PERSISTENT","RBLBANK","TATAPOWER","TITAN","VEDL","DIXON","INDIAMART","INTELLECT","NETWEB","ELECON","IEX","JWL","TEXRAIL","RAILTEL","RITES","VBL","SOBHA","BRIGADE","CUB","FORTIS","KPIL","ABB","CUMMINSIND","HINDZINC","JSWENERGY","MRF","NCC","ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BPCL","BHARTIARTL","BRITANNIA","CIPLA","DIVISLAB","DRREDDY","EICHERMOT","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDUNILVR","ICICIBANK","ITC","INDUSINDBK","INFY","JSWSTEEL","KOTAKBANK","LT","M&M","MARUTI","NTPC","NESTLEIND","ONGC","POWERGRID","RELIANCE","SBILIFE","SBIN","SUNPHARMA","TCS","TATACONSUM","TATAMOTORS","TATASTEEL","TECHM","TITAN","UPL","ULTRACEMCO","WIPRO","ABB","ACC","AUBANK","DMART","BANKBARODA","BATAINDIA","BEL","BHEL","BOSCHLTD","CESC","CGPOWER","CANBK","CHOLAFIN","DLF","FEDERALBNK","GODREJCP","HAVELLS","ICICIGI","IDFCFIRSTB","INDIGO","IOC","JINDALSTEL","JUBLFOOD","LUPIN","MOTHERSON","NHPC","NMDC","OIL","PERSISTENT","PNB","RECLTD","SAIL","SIEMENS","TATAPOWER","VEDL","VOLTAS","ZEEL","ZYDUSLIFE","360ONE","AFFLE","AMBER","ANGELONE","BSE","CDSL","CAMS","CEATLTD","CHALET","CYIENT","DIXON","ELECON","FSL","FORTIS","GSFC","GSPL","IEX","INDIAMART","INTELLECT","JWL","KAYNES","KEI","KFINTECH","KPITTECH","LODHA","MEDANTA","MUTHOOTFIN","NCC","NAUKRI","NETWEB","OLECTRA","PAYTM","POLYCAB","PRESTIGE","RBLBANK","RAILTEL","SONACOMS","SOBHA","TANLA","TATAELXSI","TATACHEM","TEXRAIL","TIMKEN","TRIDENT","TVSMOTOR","VBL","ZOMATO"]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).ewm(alpha=1/p).mean(); l=(-d.where(d<0,0)).ewm(alpha=1/p).mean()
    return 100 - (100/(1+g/l))

def analyze(sym):
    try:
        now = ist_now()
        now_min = now.hour*60 + now.minute
        if now_min < 555 or now_min > 930: return None # 9:15 to 15:30

        time.sleep(0.06)
        r=smart.searchScrip("NSE", sym)
        if not r or not r.get('data'): return None
        token=r['data'][0]['symboltoken']
        today=now.strftime("%Y-%m-%d")
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:00","todate":f"{today} 15:30"})
        if not hist or not hist.get('data') or len(hist['data'])<20: return None

        df=pd.DataFrame(hist['data'], columns=['Time','Open','High','Low','Close','Volume'])
        for c in ['Open','High','Low','Close','Volume']: df[c]=df[c].astype(float)
        df['EMA9']=df['Close'].ewm(span=9).mean()
        df['EMA15']=df['Close'].ewm(span=15).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3*df['Volume']).cumsum()/df['Volume'].cumsum()
        df['RSI']=calc_rsi(df['Close'])

        # फक्त शेवटच्या 3 Candle मध्ये शोध - On Time साठी
        for idx in range(len(df)-1, max(len(df)-4, 0), -1):
            c=df.iloc[idx]; p=df.iloc[idx-1]
            ltp=c['Close']; op=c['Open']
            if ltp<30: continue
            try: time_str=str(c['Time']).split('T')[1][:5]
            except: time_str=""

            # 🟢 BUY - आता Loose केला - Body 20% आणि RSI 50+
            # GSFC/SIEMENS सारखा पकडेलच
            buy_cross = p['Close'] <= p['VWAP'] and ltp > c['VWAP']
            buy_trend = c['EMA9'] > c['EMA15'] # फक्त 9>15 पाहिजे
            green = ltp > op
            if buy_cross and buy_trend and green and c['RSI']>=50:
                return f"🟢 BUY {sym} @ {ltp:.1f} [{time_str}] VWAP UP | 9>15 RSI{int(c['RSI'])}"

            # 🔴 SELL - COALINDIA सारखा
            sell_cross = p['Close'] >= p['VWAP'] and ltp < c['VWAP']
            sell_trend = c['EMA9'] < c['EMA15']
            red = op > ltp
            if sell_cross and sell_trend and red and c['RSI']<=52:
                return f"🔴 SELL {sym} @ {ltp:.1f} [{time_str}] VWAP DOWN | 9<15 RSI{int(c['RSI'])}"
        return None
    except: return None

results=[]
with ThreadPoolExecutor(max_workers=10) as ex:
    fut={ex.submit(analyze,s):s for s in set(SYMBOLS)}
    for f in as_completed(fut):
        r=f.result()
        if r: results.append(r)

now=ist_now().strftime("%d-%b %H:%M")
if results:
    msg=f"✅ *BSE {len(set(SYMBOLS))} Perfect {now}*\n\n" + "\n".join(results[:30])
else:
    now_min = ist_now().hour*60 + ist_now().minute
    if now_min < 555 or now_min > 930:
        msg=f"⏰ Market Closed {now}\n9:15-15:30 Active"
    else:
        # No Signal ला पण Active दाखवू नको, फक्त काही नाही तर Message नको
        msg=f"📊 BSE {len(set(SYMBOLS))} Scanner {now}\nNo Fresh Cross Last 15min - Active ✅"

send_tg(msg)
print(msg)  
