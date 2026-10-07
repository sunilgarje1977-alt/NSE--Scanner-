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
    try: requests.post(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", json={"chat_id": TELE_CHAT, "text": m, "parse_mode":"Markdown"}, timeout=20)
    except: pass

smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())

SYMBOLS = ["SIEMENS","GSFC","COALINDIA","BHEL","SAIL","SUZLON","IRFC","RVNL","IREDA","NHPC","BEL","BDL","HAL","MAZDOCK","OIL","NMDC","TATACHEM","VOLTAS","KEI","FEDERALBNK","BANKINDIA","AUROPHARMA","LUPIN","BSOFT","BHARATFORG","SONACOMS","POLYCAB","COFORGE","BSE","PAYTM","VMM","360ONE","AFFLE","AMBER","BEML","KPITTECH","TATAELXSI","LTTS","PRESTIGE","JINDALSTEL","KAYNES","KFINTECH","MASTEK","MCX","OLECTRA","TRENT","ZOMATO","DELHIVERY","MAPMYINDIA","MTARTECH","CYIENT","LICI","LODHA","BANKBARODA","CDSL","DLF","INDIGO","IRCTC","MOTHERSON","PERSISTENT","RBLBANK","TATAPOWER","TITAN","VEDL","DIXON","INDIAMART","INTELLECT","NETWEB","ELECON","IEX","JWL","TEXRAIL","RAILTEL","RITES","VBL","SOBHA","BRIGADE","CUB","FORTIS","KPIL","ABB","CUMMINSIND","HINDZINC","JSWENERGY","MRF","NCC"]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).ewm(alpha=1/p).mean(); l=(-d.where(d<0,0)).ewm(alpha=1/p).mean()
    return 100 - (100/(1+g/l))

def analyze(sym):
    try:
        now = ist_now()
        if not (555 <= now.hour*60 + now.minute <= 930): return None
        time.sleep(0.05)
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
        for idx in range(len(df)-1, max(len(df)-13, 0), -1):
            c=df.iloc[idx]; p=df.iloc[idx-1]
            if c['Close']<30: continue
            try: time_str=str(c['Time']).split('T')[1][:5]
            except: time_str=""
            # BUY - FIXED >
            if p['Close'] <= p['VWAP'] and c['Close'] > c['VWAP'] and c['EMA9']>c['EMA15'] and c['Close']>c['Open'] and c['RSI']>=50:
                return f"🟢 BUY {sym} @ {c['Close']:.1f} [{time_str}] VWAP UP | RSI{int(c['RSI'])}"
            # SELL - FIXED <
            if p['Close'] >= p['VWAP'] and c['Close'] < c['VWAP'] and c['EMA9']<c['EMA15'] and c['Open']>c['Close'] and c['RSI']<=52:
                return f"🔴 SELL {sym} @ {c['Close']:.1f} [{time_str}] VWAP DOWN | RSI{int(c['RSI'])}"
        return None
    except: return None

results=[]
with ThreadPoolExecutor(max_workers=10) as ex:
    fut={ex.submit(analyze,s):s for s in set(SYMBOLS)}
    for f in as_completed(fut):
        r=f.result()
        if r: results.append(r)

now_str=ist_now().strftime("%d-%b %H:%M")
msg = f"✅ *BSE {len(set(SYMBOLS))} {now_str}*\n\n" + "\n".join(results[:30]) if results else f"📊 BSE {len(set(SYMBOLS))} Scanner {now_str}\nNo Fresh 60min Cross - Active ✅"
send_tg(msg)
print(msg) 
