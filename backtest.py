 import os, pandas as pd, requests, pyotp
from SmartApi import SmartConnect
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import time

def clean(s): return os.getenv(s,"").strip()
obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype'].isin(['EQ']))]
tokens=nse[['token','symbol']].values.tolist()[:1000]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    rs=g/l
    return 100-(100/(1+rs))

def backtest_one(item):
    token,sym=item
    try:
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=35)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not data or 'data' not in data or len(data['data'])<300: return None
        df=pd.DataFrame(data['data'],columns=['t','o','h','l','c','v'])
        df['ema9']=df['c'].ewm(span=9).mean()
        df['ema15']=df['c'].ewm(span=15).mean()
        df['rsi']=calc_rsi(df['c'])

        daily=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_DAY","fromdate":(datetime.now()-timedelta(days=50)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not daily or 'data' not in daily: return None
        ddf=pd.DataFrame(daily['data'],columns=['t','o','h','l','c','v'])

        total=0; wins=0; sl_hit=0; pnl=0
        for i in range(50, len(df)-10):
            c=df.iloc[i]
            ema9=df['ema9'].iloc[i]; ema15=df['ema15'].iloc[i]
            ema9_p=df['ema9'].iloc[i-1]; ema15_p=df['ema15'].iloc[i-1]
            cross_up = ema9_p <= ema15_p and ema9 > ema15 and c['c'] > ema9
            cross_down = ema9_p >= ema15_p and ema9 < ema15 and c['c'] < ema9

            if not (cross_up or cross_down): continue

            # 10D 3-5% FILTER - हवं असेल तर ON कर
            STRICT_3_TO_5 = True # False केलं तर 3623 Signal येईल, True केलं तर 100-150 Signal
            if STRICT_3_TO_5:
                try:
                    d_idx = int(i/75)
                    if d_idx < 11: continue
                    base=ddf.iloc[d_idx-11:d_idx-1]
                    rng = (base['h'].max()-base['l'].min())/base['l'].min()*100
                    if rng <3 or rng >5: continue
                except: continue

            if c['rsi']<55 and c['rsi']>45: continue

            total+=1
            entry=c['c']
            fut=df.iloc[i+1:i+11]
            if cross_up:
                sl_p=c['l']; tgt=entry+(entry-sl_p)*2.5
                if (fut['h']>=tgt).any(): wins+=1; pnl+=2.5
                elif (fut['l']<=sl_p).any(): sl_hit+=1; pnl-=1
            else:
                sl_p=c['h']; tgt=entry-(sl_p-entry)*2.5
                if (fut['l']<=tgt).any(): wins+=1; pnl+=2.5
                elif (fut['h']>=sl_p).any(): sl_hit+=1; pnl-=1

        if total>0:
            return {"Symbol":sym, "Total":total, "Wins":wins, "SL":sl_hit, "WinRate":round(wins/total*100,1), "PnL":round(pnl,1)}
    except: return None

print("STARTING 30D BACKTEST...")
res=[]
with ThreadPoolExecutor(max_workers=30) as ex:
    futs={ex.submit(backtest_one,t):t for t in tokens}
    for f in as_completed(futs):
        r=f.result()
        if r: res.append(r); print(f"{r['Symbol']} - {r['Total']} - {r['WinRate']}%")

df=pd.DataFrame(res).sort_values(by="PnL", ascending=False)
print(f"\nTotal Stocks: {len(df)} | Total Signals: {df['Total'].sum()} | Avg WinRate: {df['WinRate'].mean():.1f}%")
print(df.head(10).to_string(index=False))

# Telegram
try:
    bot=clean("TELEGRAM_BOT_TOKEN"); chat=clean("TELEGRAM_CHAT_ID")
    msg=f"📊 *BACKTEST 30D - {len(df)} Stocks - {df['Total'].sum()} Signals*\nAvg WinRate: {df['WinRate'].mean():.1f}%\n\nTOP 10:\n"
    for _,r in df.head(10).iterrows():
        msg+=f"{r['Symbol']} {r['Total']}T {r['WinRate']}% {r['PnL']}PnL\n"
    requests.post(f"https://api.telegram.org/bot{bot}/sendMessage", json={"chat_id":chat, "text":msg})
except: pass
