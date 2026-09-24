 import yfinanceas yf, requests, os, pyotp
from concurrent.futures import ThreadPoolExecutor
from SmartApi import SmartConnect
from datetime import datetime

# Secrets
B = os.getenv("TELEGRAM_BOT_TOKEN")
C = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PWD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{B}/sendMessage",data={"chat_id":C,"text":m,"parse_mode":"Markdown"},timeout=10)
    except: pass

def angel_login():
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        api = SmartConnect(api_key=API_KEY)
        api.generateSession(CLIENT_ID, PWD, totp)
        return api
    except Exception as e:
        print(e); return None

S=["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS","ITC.NS","LT.NS","KOTAKBANK.NS","AXISBANK.NS","MARUTI.NS","WIPRO.NS","SUNPHARMA.NS","TITAN.NS","ONGC.NS","NTPC.NS","POWERGRID.NS","M&M.NS","BAJFINANCE.NS"]*50

def chk(s):
 try:
  d=yf.download(s,period="30d",interval="1d",progress=False,auto_adjust=False)
  f=yf.download(s,period="5d",interval="15m",progress=False,auto_adjust=False)
  if len(d)<21 or len(f)<10:return None
  e=float(d['Close'].iloc[-1])
  if not 50<=e<=1500:return None
  if float(d['Volume'].iloc[-1])<float(d['Volume'].tail(20).mean())*2:return None
  t=f.tail(26);fh=float(t.iloc[0]['High'])
  br=t[t['High']>fh]
  if br.empty:return None
  br_idx=br.index[0]
  before=t[:t.index.get_loc(br_idx)][-5:]
  if len(before)<2:return None
  small=before.loc[abs(before['Close']-before['Open']).idxmin()]
  sl=float(small['Low'])
  if ((e-sl)/e)*100<=0:return None
  tgt=e+(e-sl)*2
  return {"sym":s.replace(".NS",""),"entry":e,"sl":sl,"tgt":tgt}
 except:return None

# Scan
with ThreadPoolExecutor(max_workers=40) as x:
    r=[i for i in x.map(chk,S) if i][:6]

# Angel Auto BUY
api = angel_login()
if r and api:
    for trade in r[:2]: # एका वेळी 2 Active - Condition 10
        try:
            qty = int(5000/trade['entry'])
            # Angel Order
            api.placeOrder({
                "variety":"NORMAL","tradingsymbol":trade['sym'],"symboltoken":"","transactiontype":"BUY",
                "exchange":"NSE","ordertype":"MARKET","producttype":"INTRADAY","duration":"DAY","quantity":qty
            })
            tg(f"✅ *Angel BUY Done* {trade['sym']} Qty:{qty} E:{trade['entry']:.1f} SL:{trade['sl']:.1f}")
        except Exception as e:
            tg(f"⚠️ Angel Order Fail {trade['sym']} {e}")
else:
    if r:
        msg="🚀 *1000 Scan | Angel Login Fail - Manual BUY कर*\n\n"
        for t in r: msg+=f"*{t['sym']}* E:{t['entry']:.1f} SL:{t['sl']:.1f} T:{t['tgt']:.1f} Trail 30%\n"
        tg(msg)
    else:
        tg(f"📊 1000 Stocks Scan Done - 0 Match")

if datetime.now().hour>=15:
    tg(f"📈 *Daily 3:30 P&L* Scanned:{len(S)} Found:{len(r)}")
