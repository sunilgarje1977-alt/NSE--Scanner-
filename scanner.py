import os, requests, pandas as pd
from SmartApi import SmartConnect
import pyotp
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

def send_tg(msg):
    token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id":chat,"text":msg}, timeout=10)
    except: pass

obj=SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
totp=pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET")).now()
obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), totp)

url="https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
inst=pd.read_json(url)
nse=inst[(inst['exch_seg']=='NSE') & (inst['symbol'].str.endswith('-EQ'))].head(1000)
tokens=nse[['token','symbol']].values.tolist()

def check_bearish(df):
    curr=df.iloc[-1]; prev=df.iloc[-2]
    body=abs(curr['c']-curr['o']); rng=curr['h']-curr['l']
    uw=curr['h']-max(curr['c'],curr['o']); lw=min(curr['c'],curr['o'])-curr['l']
    maru=curr['c']<curr['o'] and body>0 and uw<body*0.2 and lw<body*0.2 and body>rng*0.7
    eng=prev['c']>prev['o'] and curr['c']<curr['o'] and curr['o']>=prev['c'] and curr['c']<=prev['o']
    shoot=body>0 and uw>=body*2 and lw<body*0.5 and curr['c']<curr['o']
    if maru: return "Bearish Marubozu"
    if eng: return "Bearish Engulfing"
    if shoot: return "Shooting Star"
    return None

def check_bullish(df):
    curr=df.iloc[-1]; prev=df.iloc[-2]
    body=abs(curr['c']-curr['o']); rng=curr['h']-curr['l']
    uw=curr['h']-max(curr['c'],curr['o']); lw=min(curr['c'],curr['o'])-curr['l']
    maru=curr['c']>curr['o'] and body>0 and uw<body*0.2 and lw<body*0.2 and body>rng*0.7
    eng=prev['c']<prev['o'] and curr['c']>curr['o'] and curr['o']<=prev['c'] and curr['c']>=prev['o']
    hammer=body>0 and lw>=body*2 and uw<body*0.5 and curr['c']>curr['o']
    if maru: return "Bullish Marubozu"
    if eng: return "Bullish Engulfing"
    if hammer: return "Hammer"
    return None

def scan_one(item):
    token,sym=item
    try:
        p={"exchange":"NSE","symboltoken":str(token),"interval":"FIVE_MINUTE","fromdate":f"{datetime.now().strftime('%Y-%m-%d')} 09:15","todate":f"{datetime.now().strftime('%Y-%m-%d')} 15:30"}
        data=obj.getCandleData(p)
        if not data or 'data' not in data or not data['data']: return None
        df=pd.DataFrame(data['data'], columns=['t','o','h','l','c','v'])
        if len(df)<25: return None
        df['ema9']=df['c'].ewm(span=9).mean(); df['ema15']=df['c'].ewm(span=15).mean()
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
        df['vol10']=df['v'].rolling(10).mean()
        d=df['c'].diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
        df['rsi']=100-(100/(1+g/l))
        last=df.iloc[-1]; prev=df.iloc[-2]
        if last['v'] < last['vol10']*1.5: return None

        # SELL LOGIC
        cross_down=prev['ema9']>=prev['ema15'] and last['ema9']<last['ema15']
        if cross_down and last['rsi']<=40 and last['c']<last['vwap'] and last['c']<last['o']:
            pat=check_bearish(df)
            if pat:
                sl=last['h']; risk=sl-last['c']; tgt=last['c']-risk*2.5
                return f"🔴 SELL {sym.replace('-EQ','')} @ {last['c']:.2f}\n{pat} | RSI {last['rsi']:.0f} | Vol {last['v']/last['vol10']:.1f}x\nSL {sl:.2f} | TGT {tgt:.2f} | 1:2.5"

        # BUY LOGIC
        cross_up=prev['ema9']<=prev['ema15'] and last['ema9']>last['ema15']
        if cross_up and last['rsi']>=60 and last['c']>last['vwap'] and last['c']>last['o']:
            pat=check_bullish(df)
            if pat:
                sl=last['l']; risk=last['c']-sl; tgt=last['c']+risk*2.5
                return f"🟢 BUY {sym.replace('-EQ','')} @ {last['c']:.2f}\n{pat} | RSI {last['rsi']:.0f} | Vol {last['v']/last['vol10']:.1f}x\nSL {sl:.2f} | TGT {tgt:.2f} | 1:2.5"
    except: return None
    return None

with ThreadPoolExecutor(max_workers=20) as ex:
    results=list(ex.map(scan_one, tokens))

hits=[r for r in results if r][:2]  # Max 2 Active Trades

if hits:
    msg=f"⚡️ NSE BUY/SELL - {datetime.now().strftime('%H:%M')} (Max 2 Active | 6/Day)\n\n" + "\n\n".join(hits)
else:
    msg=f"⚡️ NSE SCAN {datetime.now().strftime('%H:%M')} - No Buy/Sell Signal\nEMA Cross + RSI + VWAP + Pattern + 1.5x Vol"

send_tg(msg); print(msg)
