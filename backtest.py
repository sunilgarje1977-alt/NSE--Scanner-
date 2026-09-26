import os, datetime, requests, pandas as pd
from SmartApi import SmartConnect
import pyotp, time

def send_tg(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat, "text": msg}, timeout=10)
    except:
        pass

obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
totp = pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)

def get_rsi(s, p=14):
    d = s.diff()
    g = d.where(d>0,0).rolling(p).mean()
    l = -d.where(d<0,0).rolling(p).mean()
    rs = g/l
    return 100 - (100/(1+rs))

url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
inst = pd.read_json(url)
nse = inst[(inst['exch_seg']=='NSE') & (inst['symbol'].str.endswith('-EQ'))].head(150)

send_tg(f"BACKTEST V4 START: {len(nse)} stocks - 30 Days")
total=0; win=0; loss=0

for _, row in nse.iterrows():
    try:
        token = row['token']
        sym = row['symbol']
        p = {"exchange":"NSE","symboltoken":token,"interval":"ONE_MINUTE","fromdate":(datetime.datetime.now()-datetime.timedelta(days=35)).strftime("%Y-%m-%d %H:%M"),"todate":datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
        data = obj.getCandleData(p)
        df = pd.DataFrame(data['data'], columns=['time','o','h','l','c','v'])
        if len(df)<100: continue
        df['ema9']=df['c'].ewm(span=9).mean()
        df['ema15']=df['c'].ewm(span=15).mean()
        df['rsi']=get_rsi(df['c'])
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
        df['vol_avg']=df['v'].rolling(20).mean()
        for i in range(50, len(df)-20):
            last=df.iloc[i]; prev=df.iloc[i-1]
            if last['vol_avg']==0 or pd.isna(last['vol_avg']): continue
            vr=last['v']/last['vol_avg']
            rsi=last['rsi']
            if pd.isna(rsi): continue
            buy = last['c']>last['o'] and vr>=3.0 and 40<rsi<70 and last['c']>last['vwap'] and last['ema9']>last['ema15']
            sell = last['c']<last['o'] and vr>=3.0 and 30<rsi<60 and last['c']<last['vwap'] and last['ema9']<last['ema15']
            if not buy and not sell: continue
            entry=last['c']; sl=prev['l'] if buy else prev['h']
            diff=abs(entry-sl)
            if diff==0: continue
            target=entry+diff if buy else entry-diff
            fut=df.iloc[i+1:i+21]
            ht = (fut['h']>=target).any() if buy else (fut['l']<=target).any()
            hs = (fut['l']<=sl).any() if buy else (fut['h']>=sl).any()
            total+=1
            if ht and not hs: win+=1
            elif hs: loss+=1
    except:
        continue
    time.sleep(0.2)

wr = (win/total*100) if total>0 else 0
msg = f"BACKTEST V4 RESULT\n3x Vol + RSI + 1:1\nTotal:{total}\nWin:{win}\nLoss:{loss}\nWinRate:{wr:.1f}%"
send_tg(msg)
print(msg)
