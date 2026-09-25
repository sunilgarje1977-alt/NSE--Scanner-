import yfinance as yf, requests, os, pyotp, json, time
from concurrent.futures import ThreadPoolExecutor
from SmartApi import SmartConnect
from datetime import datetime
import pytz, pandas as pd

B = os.getenv("TELEGRAM_BOT_TOKEN")
C = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("ANGEL_API_KEY")
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID")
PWD = os.getenv("ANGEL_PASSWORD")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET")

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{B}/sendMessage",data={"chat_id":C,"text":m,"parse_mode":"Markdown"},timeout=15)
    except: pass

def get_1000_stocks():
    # Angel Master वरून 1000 NSE EQ Stock Auto घेईल
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data = requests.get(url, timeout=20).json()
        stocks = []
        for i in data:
            if i.get('exch_seg')=='NSE' and i.get('instrumenttype')=='' and i.get('symbol','').endswith('-EQ'):
                sym = i['symbol'].replace('-EQ','')
                # फक्त 50 ते 3000 Price Range चे - Penny नको
                if 2 < len(sym) < 15:
                    stocks.append(sym + ".NS")
            if len(stocks) >= 1000: break
        return stocks[:1000]
    except:
        # Fail झाला तर तुझे 100 Stock
        return ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS","ITC.NS","LT.NS","MARUTI.NS"]*100

def RSI(series, p=14):
    d=series.diff(); g=(d.where(d>0,0)).rolling(p).mean(); l=(-d.where(d<0,0)).rolling(p).mean(); rs=g/l; return 100-(100/(1+rs))

def chk(s):
 try:
  df = yf.download(s, period="5d", interval="15m", progress=False, auto_adjust=True)
  dfd = yf.download(s, period="1mo", interval="1d", progress=False, auto_adjust=True)
  if len(df)<50 or len(dfd)<21: return None
  df['EMA9']=df['Close'].ewm(span=9).mean(); df['EMA15']=df['Close'].ewm(span=15).mean()
  df['RSI']=RSI(df['Close']); df['VWAP']=(df['Close']*df['Volume']).cumsum()/df['Volume'].cumsum()
  last=df.iloc[-1]; prev3=df.iloc[-4:-1]
  price=float(last['Close'])
  if not 50<=price<=3000: return None
  three_high=float(prev3['High'].max())
  if price<=three_high: return None
  if ((price-three_high)/three_high)*100 < 1.2: return None
  if float(dfd['Volume'].iloc[-1]) < float(dfd['Volume'].tail(20).mean())*1.2: return None
  if last['EMA9']<=last['EMA15']: return None
  if last['RSI']<55 or last['RSI']>80: return None
  if price < float(last['VWAP']): return None
  if float(last['Close'])<=float(last['Open']): return None
  # Smallest Candle SL
  sl = float(prev3.loc[(prev3['Close']-prev3['Open']).abs().idxmin()]['Low'])
  if price-sl<=0 or ((price-sl)/price)*100>2.5: return None
  return {"sym":s.replace(".NS",""),"entry":price,"sl":sl,"tgt":price+(price-sl)*2,"tgt5":price+(price-sl)*5,"bo":((price-three_high)/three_high)*100}
 except: return None

# MAIN
S = get_1000_stocks()
print(f"Scanning {len(S)} Stocks...")

# 1000 Stock असल्याने Batch मध्ये - 100-100 चे 10 Batch
all_found=[]
for i in range(0, len(S), 100):
    batch = S[i:i+100]
    with ThreadPoolExecutor(max_workers=10) as ex:
        found = [r for r in ex.map(chk, batch) if r]
        all_found.extend(found)
    time.sleep(1) # Yahoo Block होऊ नये म्हणून 1 sec Gap

all_found = sorted(all_found, key=lambda x: x['bo'], reverse=True)[:2] # Top 2

# Angel Auto Buy
try:
    totp=pyotp.TOTP(TOTP_SECRET).now(); api=SmartConnect(api_key=API_KEY); api.generateSession(CLIENT_ID,PWD,totp)
    angel_ok=True
except: angel_ok=False; api=None

ist=pytz.timezone('Asia/Kolkata'); now=datetime.now(ist).strftime("%H:%M:%S")

if all_found and angel_ok:
    msg=f"🚀 *1000 SCAN DONE {now} | Angel BUY*\nFound:{len(all_found)}/1000\n\n"
    for t in all_found:
        try:
            qty=int(5000/t['entry'])
            api.placeOrder({"variety":"NORMAL","tradingsymbol":t['sym'],"symboltoken":"","transactiontype":"BUY","exchange":"NSE","ordertype":"MARKET","producttype":"INTRADAY","duration":"DAY","quantity":qty})
            msg+=f"✅ *{t['sym']}* E:{t['entry']:.1f} SL:{t['sl']:.1f} T:{t['tgt']:.1f} T5:{t['tgt5']:.1f} BO:{t['bo']:.2f}%\n"
        except Exception as e: msg+=f"⚠️ {t['sym']} Fail {e}\n"
    tg(msg)
else:
    if all_found: tg(f"🚀 *1000 Scan Found* {all_found[0]['sym']} E:{all_found[0]['entry']:.1f} SL:{all_found[0]['sl']:.1f} - Angel Login Fail")
    else: tg(f"📊 *1000 Scan {now} Active:0/2 Done:0/6* 0 Match - 3 Candle+RSI55+EMA9>15+VWAP+1.2x Filter")
