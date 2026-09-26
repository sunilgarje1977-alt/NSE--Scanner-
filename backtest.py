# BACKTEST - Last 30 Days Intraday 1:2:5 Check
import os, pyotp, pandas as pd
from SmartApi import SmartConnect
from datetime import datetime, timedelta
import requests

API_KEY=os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD=os.getenv("ANGEL_PASSWORD","")
TOTP=os.getenv("ANGEL_TOTP_SECRET","").strip().replace(" ","").upper()
BOT=os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT=os.getenv("TELEGRAM_CHAT_ID","")

def tg(m): requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id":CHAT,"text":m})

obj=SmartConnect(api_key=API_KEY)
obj.generateSession(CLIENT_ID,PASSWORD,pyotp.TOTP(TOTP).now())
master=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")

# तुझी List
SYMBOLS=["RELIANCE","TCS","INFY","SBIN","SKFINDIA","GLAXO","HDFCBANK","ICICIBANK","TATAMOTORS","HAL","BEL"]
nse=master[master['exch_seg']=='NSE']
TMap={r['symbol'].replace('-EQ',''):str(r['token']) for _,r in nse.iterrows() if r['symbol'].replace('-EQ','') in SYMBOLS}

tg("BACKTEST START - 30 Days Intraday...")

wins=0; loss=0; total=0
for sym in SYMBOLS:
  token=TMap.get(sym)
  if not token: continue
  try:
    p={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=35)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d 15:30")}
    d=obj.getCandleData(p).get('data')
    if not d: continue
    df=pd.DataFrame(d, columns=['date','open','high','low','close','volume'])
    df['ema9']=df['close'].ewm(9).mean()
    df['ema15']=df['close'].ewm(15).mean()
    df['high20']=df['high'].rolling(20).max()
    df['low20']=df['low'].rolling(20).min()
    for i in range(30, len(df)-5):
      last=df.iloc[i]; prev=df.iloc[i-1]
      if last['close']>df['high20'].iloc[i-1] and last['ema9']>last['ema15'] and prev['ema9']<=prev['ema15']:
        total+=1
        risk=last['close']-last['low']
        future=df.iloc[i+1:i+6]
        hit=False
        for _,c in future.iterrows():
          if c['low']<=last['low']: loss+=1; hit=True; break
          if c['high']>=last['close']+risk*2: wins+=1; hit=True; break
        if not hit: loss+=1
  except: pass

tg(f"BACKTEST RESULT 30 DAYS\nTotal: {total}\nWins (1:2): {wins}\nLoss: {loss}\nWinRate: {wins/total*100 if total else 0:.1f}%")
