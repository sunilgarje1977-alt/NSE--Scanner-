import os, requests, pandas as pd
from SmartApi import SmartConnect
import pyotp
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

def clean(s): return os.getenv(s,"").strip()  # \n काढून टाकेल

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{clean('TELEGRAM_BOT_TOKEN')}/sendMessage", data={"chat_id":clean('TELEGRAM_CHAT_ID'),"text":m}, timeout=5)
    except: pass

obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['symbol'].str.endswith('-EQ'))].head(1000)
tokens=nse[['token','symbol']].values.tolist()

def bear_pat(df):
    c=df.iloc[-1]; p=df.iloc[-2]; body=abs(c['c']-c['o']); rng=c['h']-c['l']; uw=c['h']-max(c['c'],c['o']); lw=min(c['c'],c['o'])-c['l']
    if c['c']<c['o'] and uw<body*0.2 and lw<body*0.2 and body>rng*0.7: return "Bearish Marubozu"
    if p['c']>p['o'] and c['c']<c['o'] and c['o']>=p['c'] and c['c']<=p['o']: return "Bearish Engulfing"
    if body>0 and uw>=body*2 and lw<body*0.5 and c['c']<c['o']: return "Shooting Star"
    return None

def bull_pat(df):
    c=df.iloc[-1]; p=df.iloc[-2]; body=abs(c['c']-c['o']); rng=c['h']-c['l']; uw=c['h']-max(c['c'],c['o']); lw=min(c['c'],c['o'])-c['l']
    if c['c']>c['o'] and uw<body*0.2 and lw<body*0.2 and body>rng*0.7: return "Bullish Marubozu"
    if p['c']<p['o'] and c['c']>c['o'] and c['o']<=p['c'] and c['c']>=p['o']: return "Bullish Engulfing"
    if body>0 and lw>=body*2 and uw<body*0.5 and c['c']>c['o']: return "Hammer"
    return None

def scan_one(item):
    token,sym=item
    try:
        d=obj.getCandleData({"exchange":"NSE","symboltoken":str(token),"interval":"FIVE_MINUTE","fromdate":f"{datetime.now().strftime('%Y-%m-%d')} 09:15","todate":f"{datetime.now().strftime('%Y-%m-%d')} 15:30"})
        if not d or not d.get('data'): return None
        df=pd.DataFrame(d['data'], columns=['t','o','h','l','c','v'])
        if len(df)<25: return None
        df['ema9']=df['c'].ewm(span=9).mean(); df['ema15']=df['c'].ewm(span=15).mean()
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum(); df['vol10']=df['v'].rolling(10).mean()
        diff=df['c'].diff(); up=diff.where(diff>0,0).rolling(14).mean(); down=-diff.where(diff<0,0).rolling(14).mean()
        df['rsi']=100-(100/(1+up/down))
        last=df.iloc[-1]; prev=df.iloc[-2]
        if last['v'] < last['vol10']*1.5: return None
        if prev['ema9']>=prev['ema15'] and last['ema9']<last['ema15'] and last['rsi']<=40 and last['c']<last['vwap'] and last['c']<last['o']:
            pat=bear_pat(df)
            if pat:
                tgt=last['c']-(last['h']-last['c'])*2.5
                return f"🔴 SELL {sym.replace('-EQ','')} @ {last['c']:.1f}\n{pat} | RSI {last['rsi']:.0f} | SL {last['h']:.1f} TGT {tgt:.1f}"
        if prev['ema9']<=prev['ema15'] and last['ema9']>last['ema15'] and last['rsi']>=60 and last['c']>last['vwap'] and last['c']>last['o']:
            pat=bull_pat(df)
            if pat:
                tgt=last['c']+(last['c']-last['l'])*2.5
                return f"🟢 BUY {sym.replace('-EQ','')} @ {last['c']:.1f}\n{pat} | RSI {last['rsi']:.0f} | SL {last['l']:.1f} TGT {tgt:.1f}"
    except: return None

with ThreadPoolExecutor(max_workers=50) as ex:
    res=list(ex.map(scan_one, tokens))

hits=[r for r in res if r][:2]
msg=f"⚡️ FAST BUY/SELL {datetime.now().strftime('%H:%M')} | 1000 Stocks | Max 2\n\n" + ("\n\n".join(hits) if hits else "No Signal")
send_tg(msg); print(msg)
