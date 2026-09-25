import yfinance as yf, requests, os, pyotp, json
from concurrent.futures import ThreadPoolExecutor
from SmartApi import SmartConnect
from datetime import datetime
import pytz

B=os.getenv("TELEGRAM_BOT_TOKEN"); C=os.getenv("TELEGRAM_CHAT_ID")
API_KEY=os.getenv("ANGEL_API_KEY"); CLIENT_ID=os.getenv("ANGEL_CLIENT_ID")
PWD=os.getenv("ANGEL_PASSWORD"); TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET","").replace(" ","").strip()
IST=pytz.timezone('Asia/Kolkata'); STATE_FILE="trades_today.json"

def tg(m):
 try: requests.post(f"https://api.telegram.org/bot{B}/sendMessage",data={"chat_id":C,"text":m},timeout=15)
 except: pass

def angel_login():
 try:
  api=SmartConnect(api_key=API_KEY); api.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())
  master=requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",timeout=20).json()
  mp={d['symbol'].replace('-EQ',''):d['token'] for d in master if d['exch_seg']=='NSE' and d['symbol'].endswith('-EQ')}
  return api,mp
 except: return None,{}

def load_state():
 try:
  if not os.path.exists(STATE_FILE): return {"date":datetime.now(IST).strftime('%Y-%m-%d'),"trades":[],"active":[]}
  with open(STATE_FILE,'r') as f: s=json.load(f)
  if s.get("date")!=datetime.now(IST).strftime('%Y-%m-%d'): return {"date":datetime.now(IST).strftime('%Y-%m-%d'),"trades":[],"active":[]}
  return s
 except: return {"date":datetime.now(IST).strftime('%Y-%m-%d'),"trades":[],"active":[]}

def save_state(s):
 with open(STATE_FILE,'w') as f: json.dump(s,f)

try:
 master=requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json",timeout=20).json()
 real_eq=[d['symbol'].replace('-EQ','') for d in master if d['exch_seg']=='NSE' and d['symbol'].endswith('-EQ')][:1000]
 S=[s+".NS" for s in real_eq]
except: S=["RELIANCE.NS","TCS.NS","INFY.NS"]*333

def chk(s):
 try:
  d=yf.download(s,period="40d",interval="1d",progress=False,auto_adjust=False,threads=False)
  f=yf.download(s,period="5d",interval="15m",progress=False,auto_adjust=False,threads=False)
  if hasattr(d.columns,'levels'): d.columns=d.columns.droplevel(1)
  if hasattr(f.columns,'levels'): f.columns=f.columns.droplevel(1)
  if len(d)<30 or len(f)<30: return None
  e=float(d['Close'].iloc[-1]); vol_today=float(d['Volume'].iloc[-1])
  if (e*vol_today)/10000000<10: return None
  if not 80<=e<=3000: return None
  d['EMA9']=d['Close'].ewm(span=9,adjust=False).mean(); d['EMA15']=d['Close'].ewm(span=15,adjust=False).mean()
  if float(d['EMA9'].iloc[-1])<float(d['EMA15'].iloc[-1]): return None
  vol_avg=float(d['Volume'].tail(20).mean())
  if vol_today/vol_avg<1.5: return None
  f['Typical']=(f['High']+f['Low']+f['Close'])/3; f['VP']=f['Typical']*f['Volume']
  if float(f.iloc[-1]['Close']) < f['VP'].tail(26).sum()/f['Volume'].tail(26).sum(): return None
  delta=d['Close'].diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
  rsi=100-(100/(1+gain/loss)); rsi_val=float(rsi.iloc[-1])
  if rsi_val<55 or rsi_val>82: return None
  t=f.tail(26); fh=float(t.iloc[0:4]['High'].max())
  if (float(f.iloc[-1]['Close'])-fh)/fh*100<0.8: return None
  rng=float(f.iloc[-1]['High'])-float(f.iloc[-1]['Low']); body=abs(float(f.iloc[-1]['Close'])-float(f.iloc[-1]['Open']))
  if rng==0 or body/rng<0.60 or float(f.iloc[-1]['Close'])<float(f.iloc[-1]['Open']): return None
  br=t[t['High']>fh]
  if br.empty: return None
  before=t.iloc[:t.index.get_loc(br.index[0])][-5:]; small=before.loc[abs(before['Close']-before['Open']).idxmin()]
  sl=float(small['Low'])
  if ((e-sl)/e)*100<=0 or ((e-sl)/e)*100>4: return None
  tgt=e+(e-sl)*2.5
  return {"sym":s.replace(".NS",""),"entry":round(e,1),"sl":round(sl,1),"tgt":round(tgt,1)}
 except: return None

state=load_state(); now_ist=datetime.now(IST)
can_take=2-len(state["active"]); daily_left=6-len(state["trades"])-len(state["active"])
if can_take>0 and daily_left>0 and now_ist.hour<15:
 with ThreadPoolExecutor(max_workers=20) as x: r=[i for i in x.map(chk,S) if i]
 r=r[:can_take]
 if r:
  api,token_map=angel_login()
  for trade in r[:daily_left]:
   trade['qty']=max(1,int(5000/trade['entry'])); trade['time']=now_ist.strftime('%H:%M'); trade['date']=state['date']
   if api:
    try:
     token=token_map.get(trade['sym'],"")
     api.placeOrder({"variety":"NORMAL","tradingsymbol":trade['sym'],"symboltoken":token,"transactiontype":"BUY","exchange":"NSE","ordertype":"MARKET","producttype":"INTRADAY","duration":"DAY","quantity":trade['qty']})
     tg(f"Angel BUY {trade['sym']} E:{trade['entry']} SL:{trade['sl']}")
    except: tg(f"Paper BUY {trade['sym']} E:{trade['entry']}")
   else: tg(f"Paper BUY {trade['sym']} E:{trade['entry']}")
   state["active"].append(trade); save_state(state)
save_state(state)
tg(f"Scan {now_ist.strftime('%H:%M')} Active:{len(state['active'])}/2 Done:{len(state['trades'])}/6")
