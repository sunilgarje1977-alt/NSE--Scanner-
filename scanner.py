from SmartApi import SmartConnect
import pyotp, requests, os, json, pandas as pd
from datetime import datetime, timedelta
import time

# --- SECRETS ---
API_KEY=os.getenv("ANGEL_API_KEY")
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID")
PASSWORD=os.getenv("ANGEL_PASSWORD")
TOTP_SECRET=os.getenv("ANGEL_TOTP")
BOT=os.getenv("TELEGRAM_BOT_TOKEN"); CHAT=os.getenv("TELEGRAM_CHAT_ID")

def tg(m):
 try: requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",data={"chat_id":CHAT,"text":m,"parse_mode":"Markdown"},timeout=10)
 except: pass

# Angel Login
obj=SmartConnect(api_key=API_KEY)
totp=pyotp.TOTP(TOTP_SECRET).now()
obj.generateSession(CLIENT_ID, PASSWORD, totp)
print("Angel Login Done")

CAPITAL=100000; LEVERAGE=5; MAX_DAY=6; MAX_OPEN=2; RISK=0.02

def rsi(s,p=14):
 d=s.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
 return 100-(100/(1+g.ewm(alpha=1/p).mean()/l.ewm(alpha=1/p).mean()))

def smi(df):
 h=df['high'].rolling(10).max(); l=df['low'].rolling(10).min()
 sm=100*(df['close']-(h+l)/2)/((h-l)/2); return sm, sm.rolling(3).mean()

def get_candles(token, interval, days=5):
 try:
  params={"exchange":"NSE","symboltoken":token,"interval":interval,"fromdate":(datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d %H:%M"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
  data=obj.getCandleData(params)
  df=pd.DataFrame(data['data'],columns=['time','open','high','low','close','volume'])
  df['time']=pd.to_datetime(df['time'])
  return df
 except: return None

def chart_pattern(df):
 last20=df.tail(20); high=last20['high'].max(); low=last20['low'].min()
 box=(high-low)/low<0.04 if low>0 else False
 lows=last20['low'].tail(5).tolist()
 higher=lows[-1]>lows[-3] if len(lows)>=5 else False
 vol_expand=float(df['volume'].iloc[-1])>float(df['volume'].tail(20).mean())*1.8
 return box and higher and vol_expand, high

def check_stock(item):
 # item = {"symbol":"SUNTV-EQ","token":"38145"}
 try:
  f=get_candles(item['token'],"FIVE_MINUTE",5)
  d=get_candles(item['token'],"ONE_DAY",60)
  if f is None or d is None or len(f)<78 or len(d)<30: return None
  e=float(f['close'].iloc[-1])
  if not 50<=e<=2500: return None
  
  f['EMA9']=f['close'].ewm(span=9).mean(); f['EMA15']=f['close'].ewm(span=15).mean()
  f['RSI']=rsi(f['close']); f['VWAP']=(f['close']*f['volume']).cumsum()/f['volume'].cumsum()
  f['SMI'],f['SIG']=smi(f)
  
  av=float(d['volume'].tail(20).mean()); dv=float(d['volume'].iloc[-1])
  first=f[f['time'].dt.time.between(pd.to_datetime("09:15").time(), pd.to_datetime("09:30").time())]
  if len(first)<3: return None
  f15h=float(first['high'].max())
  
  last=f.iloc[-1]
  c1=e>f15h*1.005
  c2=dv>av*1.5
  c4=float(last['close'])>float(last['open'])
  c5=55<=float(f['RSI'].iloc[-1])<=68
  c6=float(f['SMI'].iloc[-1])>float(f['SIG'].iloc[-1])
  c7=float(f['EMA9'].iloc[-1])>float(f['EMA15'].iloc[-1])
  c8=e>float(f['VWAP'].iloc[-1]) and all(f['close'].tail(3)>f['VWAP'].tail(3))
  is_chart,box_h=chart_pattern(f)
  c10=is_chart and e>box_h*1.005
  
  score=sum([c1,c2,c4,c5,c6,c7,c8,c10])
  if score>=6 and c1 and c2 and c8 and c10:
    before=f.iloc[-8:-3]
    small=before.loc[abs(before['close']-before['open']).idxmin()]
    sl=float(small['low'])
    if e-sl<=0 or (e-sl)/e>0.04: return None
    return {"sym":item['symbol'].replace("-EQ",""),"token":item['token'],"e":e,"sl":sl,"t3":e+(e-sl)*3,"t5":e+(e-sl)*5,"vol":dv/av,"score":score}
 except Exception as ex:
  print(f"Err {item['symbol']} {ex}"); return None

# --- MAIN ---
# Summary 3:35 PM
if datetime.utcnow().hour==10 and datetime.utcnow().minute<=10:
 if os.path.exists("trades.json"):
  tr=json.load(open("trades.json"))
  if tr:
   pnl=0; msg="📊 *Angel FINAL Summary - 6 Trade*\n\n"
   for t in tr:
    df=get_candles(t['token'],"FIVE_MINUTE",1)
    live=float(df['close'].iloc[-1]) if df is not None else t['entry']
    exit_p=t.get('exit',live); p=(exit_p-t['entry'])*t['qty']; pnl+=p
    msg+=f"{t['sym']} {p:+.0f}Rs [{t['status']}]\n"
   msg+=f"\n*Total P&L: {pnl:+.0f} Rs*\n1L * 5x = 5L"; tg(msg)
 open("trades.json","w").write("[]"); exit()

# Load NSE 1000 Tokens (Angel Master)
try:
 url="https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
 data=requests.get(url,timeout=20).json()
 nse_eq=[x for x in data if x['exch_seg']=='NSE' and x['symbol'].endswith('-EQ')][:1000]
 stocks=[{"symbol":x['symbol'],"token":x['token']} for x in nse_eq]
except:
 stocks=[{"symbol":"RELIANCE-EQ","token":"2885"},{"symbol":"SUNTV-EQ","token":"38145"},{"symbol":"TCS-EQ","token":"11536"}]*100

if not os.path.exists("trades.json"): open("trades.json","w").write("[]")
trades=json.load(open("trades.json"))
open_tr=[t for t in trades if t['status']=='OPEN']

# Trailing SL Check
for t in open_tr:
 try:
  df=get_candles(t['token'],"FIVE_MINUTE",1)
  live=float(df['close'].iloc[-1]); ema9=float(df['close'].ewm(span=9).mean().iloc[-1]); swing=float(df['low'].tail(3).min())
  new_sl=max(t['sl'],ema9*0.998,swing)
  if live<=t['sl']: t['status']='CLOSED_SL'; t['exit']=live; tg(f"❌ SL Hit *{t['sym']}* Loss {(live-t['entry'])*t['qty']:+.0f}")
  elif live>=t['t3'] and t['sl']<t['entry']: t['sl']=t['entry']; tg(f"✅ *{t['sym']}* 3x Done SL->Cost Trail ON 5x {t['t5']:.1f}")
  elif new_sl>t['sl']: t['sl']=new_sl
 except: pass

if len(trades)>=MAX_DAY or len(open_tr)>=MAX_OPEN:
 open("trades.json","w").write(json.dumps(trades)); exit()

# Scan
results=[]
for s in stocks[:200]: # 200 per run to avoid rate limit, next run next 200
 res=check_stock(s)
 if res: results.append(res)
 time.sleep(0.2)

for sig in sorted(results,key=lambda x:x['vol'],reverse=True):
 if len([t for t in trades if t['status']=='OPEN'])>=MAX_OPEN or len(trades)>=MAX_DAY: break
 if sig['sym'] in [t['sym'] for t in trades if t['status']=='OPEN']: continue
 qty=int((CAPITAL*RISK)/(sig['e']-sig['sl'])); qty=min(qty,int((CAPITAL*LEVERAGE/2)/sig['e']))
 if qty<=0: continue
 trades.append({"sym":sig['sym'],"token":sig['token'],"entry":sig['e'],"sl":sig['sl'],"qty":qty,"t3":sig['t3'],"t5":sig['t5'],"status":"OPEN"})
 tg(f"🚀 *ANGEL {len(trades)}/{MAX_DAY} Score {sig['score']}/8*\n*{sig['sym']}* Qty:{qty} Vol:{sig['vol']:.1f}x\nE:{sig['e']:.1f} SL:{sig['sl']:.1f}(Small Low)\nTGT 3x:{sig['t3']:.1f} 5x:{sig['t5']:.1f}\nTrail 9EMA")

open("trades.json","w").write(json.dumps(trades)) 
