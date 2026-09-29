# V23 FASTEST - 15 SEC SCAN
import os,requests,pyotp,pandas as pd,time
from SmartApi import SmartConnect
from datetime import datetime,timedelta
from concurrent.futures import ThreadPoolExecutor,as_completed
API_KEY=os.getenv("ANGEL_API_KEY","").strip();CLIENT_ID=os.getenv("ANGEL_CLIENT_ID","").strip();PASSWORD=os.getenv("ANGEL_PASSWORD","");TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET","").strip().replace(" ","").upper();BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","");CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","")
MAX_TRADES=8;MAX_ACTIVE=2;ACTIVE=[];TOTAL=0
ALL_SYMBOLS="""RELIANCE TCS HDFCBANK ICICIBANK INFY ITC SBIN BHARTIARTL LT BAJFINANCE MARUTI TITAN SUNPHARMA WIPRO ULTRACEMCO NTPC POWERGRID TATAMOTORS TATASTEEL JSWSTEEL HCLTECH BAJAJFINSV ASIANPAINT ONGC ADANIENT ADANIPORTS COALINDIA GRASIM HINDALCO HINDUNILVR CIPLA DIVISLAB DRREDDY EICHERMOT BPCL BRITANNIA HEROMOTOCO ICICIPRULI SBILIFE HDFCLIFE LTIM TRENT VEDL INDUSINDBK AXISBANK KOTAKBANK BAJAJ-AUTO APOLLOHOSP TATACONSUM NESTLEIND JSWENERGY NHPC SJVN GMRINFRA IDFCFIRSTB FEDERALBNK AUBANK INDIANB BANKINDIA UNIONBANK CANBK MAHABANK PNB BANKBARODA RECLTD PFC IRFC RVNL IRCTC HAL BEL BHEL SAIL TATAPOWER ADANIGREEN ADANIPOWER IDEA YESBANK SUZLON JIOFIN ZOMATO NYKAA PAYTM POLICYBZR DELHIVERY NAUKRI INDIAMART LTF MUTHOOTFIN MANAPPURAM CHOLAFIN SHRIRAMFIN TATACHEM DEEPAKNTR AARTIIND ATUL SRF PIIND UPL COROMANDEL ABB SIEMENS VOLTAS DIXON TATATECH TATAELXSI KPITTECH COFORGE PERSISTENT MPHASIS LTTS IEX MCX BSE CAMS CDSL ANGELONE DLF GODREJPROP DMART POLYCAB HAVELLS INDHOTEL M&M TVSMOTOR MOTHERSON MRF MAZDOCK BDL DAMCAPITAL HUDCO ALOKINDS CENTRALBK""".split()
RESULT_TODAY=["HUDCO","RECLTD","DAMCAPITAL","MAZDOCK","ALOKINDS","CENTRALBK"]
def tg(m):
 try:requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":m},timeout=5)
 except:pass
 print(m,flush=True)
obj=SmartConnect(api_key=API_KEY);obj.generateSession(CLIENT_ID,PASSWORD,pyotp.TOTP(TOTP_SECRET).now())
tg(f"🚀 V23 FAST START {datetime.now().strftime('%H:%M')} | {len(ALL_SYMBOLS)} STOCKS")
def get_tokens():
 try:df=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json");return {r['symbol'].replace('-EQ',''):str(r['token']) for _,r in df.iterrows() if r['exch_seg']=='NSE' and str(r['symbol']).endswith('-EQ') and r['symbol'].replace('-EQ','') in ALL_SYMBOLS}
 except:return{}
TOKENS=get_tokens()
def indi(df):
 c=df["close"];df["ema9"]=c.ewm(9).mean();df["ema15"]=c.ewm(15).mean();df["ema21"]=c.ewm(21).mean();df["vwap"]=(c*df["volume"]).cumsum()/df["volume"].cumsum();df["macd"]=c.ewm(12).mean()-c.ewm(26).mean();df["macd_sig"]=df["macd"].ewm(9).mean();d=c.diff();g=d.where(d>0,0).rolling(14).mean();l=-d.where(d<0,0).rolling(14).mean();df["rsi"]=100-(100/(1+g/l));df["vol20"]=df["volume"].rolling(20).mean();return df
def get_sl(ltp,side,df):
 cl=df["low"].iloc[-3:].min();ch=df["high"].iloc[-3:].max();min_sl=1.2 if ltp<50 else 1.0 if ltp<200 else 0.85 if ltp<600 else 0.75
 if side=="BUY":sl_p=ltp*(1-min_sl/100);sl=sl_p if (ltp-cl)/ltp*100<min_sl else min(cl,sl_p);sl_pct=(ltp-sl)/ltp*100;return round(sl,2),round(ltp*(1+sl_pct/100),2),round(ltp*(1+sl_pct*1.5/100),2),round(sl_pct,2)
 else:sl_p=ltp*(1+min_sl/100);sl=sl_p if (ch-ltp)/ltp*100<min_sl else max(ch,sl_p);sl_pct=(sl-ltp)/ltp*100;return round(sl,2),round(ltp*(1-sl_pct/100),2),round(ltp*(1-sl_pct*1.5/100),2),round(sl_pct,2)
def scan_one(sym):
 if sym in [a["symbol"] for a in ACTIVE]:return None
 token=TOKENS.get(sym)
 if not token:return None
 try:
  p={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
  d=obj.getCandleData(p)
  if not d or not d.get('data'):return None
  df=pd.DataFrame(d['data'],columns=['date','open','high','low','close','volume'])
  if len(df)<30:return None
  df=indi(df);last=df.iloc[-1];prev=df.iloc[-2];ltp=last["close"];do=df["open"].iloc[-1];pc=df["close"].iloc[-2];dh=df["high"].iloc[-1];dl=df["low"].iloc[-1];dg=(ltp-do)/do*100;gap=(do-pc)/pc*100 if pc else 0;m5=(ltp-prev["close"])/prev["close"]*100;rec=(ltp-dl)/dl*100;v20=df["volume"].iloc[-1]/last["vol20"] if last["vol20"]>0 else 1;v5=df["volume"].iloc[-1]/df["volume"].iloc[-6:-1].mean() if len(df)>6 else 1;high_52=df["high"].max();near_52h=(ltp/high_52)*100;low_52=df["low"].min();near_52l=(ltp/low_52)*100
  if abs(gap)>5:return None
  buy=0;sell=0;br=[];sr=[]
  if last["ema9"]>last["ema15"]>last["ema21"]:buy+=1.5;br.append("TREND UP")
  if last["ema9"]<last["ema15"]<last["ema21"]:sell+=1.5;sr.append("TREND DN")
  if ltp>last["vwap"]:buy+=1.2;br.append("VWAP+")
  else:sell+=1.2;sr.append("VWAP-")
  if last["macd"]>last["macd_sig"]:buy+=1.2;br.append("MACD+")
  else:sell+=1.2;sr.append("MACD-")
  if dg>=0.5:buy+=1.2;br.append(f"DAY+{dg:.1f}%")
  if dg<=-0.5:sell+=1.2;sr.append(f"DAY{dg:.1f}%")
  if m5>=0.15:buy+=1.0;br.append(f"5M+{m5:.2f}%")
  if m5<=-0.15:sell+=1.0;sr.append(f"5M{m5:.2f}%")
  if rec>=1.0:buy+=1.0;br.append(f"REC {rec:.1f}%")
  if m5>=0.5 and rec>=1.0:buy+=2.5;br.append("BOUNCE")
  if sym in RESULT_TODAY and v20>=2.0:buy+=3;sell+=3;br.append("RESULT");sr.append("RESULT")
  if v20>=2.5:buy+=2.5 if dg>0 else 0; sell+=2.5 if dg<0 else 0
  if v5>=2.0 and ltp>=dh*0.992:buy+=3.5;br.append("DAY-H BLAST")
  if last["vwap"]>last["ema9"]>last["ema15"]:buy+=3.5;br.append("VWAP>9>15 SUPER BUY")
  if last["vwap"]<last["ema9"]<last["ema15"]:sell+=3.5;sr.append("VWAP<9<15 SUPER SELL")
  if near_52h>=98:buy+=4;br.append(f"52W-H {near_52h:.1f}%")
  if near_52l<=102:sell+=4;sr.append(f"52W-L {near_52l:.1f}%")
  if near_52h>=98 and v20>=3 and dg>=2:buy+=5;br.append("JACKPOT 🚀")
  if buy>=3 and buy>sell+0.5:sl,t1,t2,slp=get_sl(ltp,"BUY",df);return {"side":"BUY","symbol":sym,"entry":ltp,"sl":sl,"t1":t1,"t2":t2,"slp":slp,"reason":"|".join(br),"score":buy,"status":"ACTIVE"}
  if sell>=3 and sell>buy+0.5:sl,t1,t2,slp=get_sl(ltp,"SELL",df);return {"side":"SELL","symbol":sym,"entry":ltp,"sl":sl,"t1":t1,"t2":t2,"slp":slp,"reason":"|".join(sr),"score":sell,"status":"ACTIVE"}
 except:return None
with ThreadPoolExecutor(max_workers=50) as ex:
 fut={ex.submit(scan_one,s):s for s in ALL_SYMBOLS}
 for f in as_completed(fut):
  r=f.result()
  if r and len(ACTIVE)<MAX_ACTIVE and TOTAL<MAX_TRADES:ACTIVE.append(r);TOTAL+=1;tg(f"🚀 FAST {r['side']} {r['symbol']} @{r['entry']} SL {r['sl']}({r['slp']}%) T1 {r['t1']} T2 {r['t2']} | {r['reason']} S:{r['score']:.1f}")
print("DONE FAST")
