import os, pandas as pd, requests, time
from SmartApi import SmartConnect
import pyotp
from datetime import datetime, timedelta
from collections import Counter

def clean(s): return os.getenv(s,"").strip()
def send_telegram(msg):
    try:
        token=clean("TELEGRAM_BOT_TOKEN"); chat=clean("TELEGRAM_CHAT_ID")
        for i in range(0, len(msg), 4000):
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id":chat,"text":msg[i:i+4000],"parse_mode":"Markdown"}, timeout=15)
            time.sleep(1)
    except Exception as e: print(e)

obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

print("Downloading Master...")
try:
    data=requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
    nse=[d for d in data if d.get('exch_seg')=='NSE' and d.get('instrumenttype')=='' and d.get('symbol','').endswith('-EQ')]
    stocks=[(d['name'], d['token']) for d in nse[:1000]]
    print(f"Found {len(stocks)}")
except:
    stocks=[("RELIANCE","2885"),("TCS","11536"),("INFY","1594")]

def get_history(token, days=30):
    try:
        end=datetime.now(); start=end-timedelta(days=days)
        d=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":start.strftime('%Y-%m-%d 09:15'),"todate":end.strftime('%Y-%m-%d 15:30')})
        if not d or not d.get('data'): return pd.DataFrame()
        return pd.DataFrame(d['data'], columns=['t','o','h','l','c','v'])
    except: return pd.DataFrame()

results=[]; total_signals=0
for idx, (sym, tok) in enumerate(stocks):
    print(f"{idx+1}/{len(stocks)} {sym}")
    df=get_history(tok,30)
    if len(df)<50: continue
    df['ema9']=df['c'].ewm(span=9).mean()
    df['ema15']=df['c'].ewm(span=15).mean()
    df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
    df['vol10']=df['v'].rolling(10).mean()
    diff=df['c'].diff(); up=diff.where(diff>0,0).rolling(14).mean(); down=-diff.where(diff<0,0).rolling(14).mean()
    df['rsi']=100-(100/(1+up/down))
    trades=[]; pnl=0
    for i in range(25,len(df)-10):
        r=df.iloc[i]; p=df.iloc[i-1]
        if r['v'] < r['vol10']*1.5: continue
        is_sell = p['ema9']>=p['ema15'] and r['ema9']<r['ema15'] and r['rsi']<=40 and r['c']<r['vwap'] and r['c']<r['o']
        is_buy = p['ema9']<=p['ema15'] and r['ema9']>r['ema15'] and r['rsi']>=60 and r['c']>r['vwap'] and r['c']>r['o']
        if not (is_sell or is_buy): continue
        entry=r['c']
        if is_sell: sl=r['h']; risk=abs(entry-sl); t1=entry-risk*1; t2=entry-risk*2.5
        else: sl=r['l']; risk=abs(entry-sl); t1=entry+risk*1; t2=entry+risk*2.5
        res="No Hit"; ret=0
        for j in range(i+1, min(i+11,len(df))):
            f=df.iloc[j]
            if is_sell:
                if f['h']>=sl: res="SL"; ret=-1; break
                if f['l']<=t2: res="T2 WIN"; ret=2.5; break
                if f['l']<=t1: res="T1 WIN"; ret=1; break
            else:
                if f['l']<=sl: res="SL"; ret=-1; break
                if f['h']>=t2: res="T2 WIN"; ret=2.5; break
                if f['h']>=t1: res="T1 WIN"; ret=1; break
        trades.append(res); pnl+=ret
    if trades:
        c=Counter(trades); wins=c['T1 WIN']+c['T2 WIN']; total=len(trades); wr=wins/total*100 if total else 0
        results.append({"Symbol":sym,"Total":total,"Wins":wins,"SL":c['SL'],"WinRate":wr,"PnL":pnl})
        total_signals+=total
    time.sleep(0.2)

import pandas as pd
df_res=pd.DataFrame(results).sort_values(by="PnL", ascending=False)
df_res.to_csv("backtest_1000_results.csv", index=False)
top10=df_res.head(10).to_string(index=False)
msg=f"📊 *NSE 1000 STOCKS BACKTEST - 30 DAYS*\nTotal Stocks: {len(results)}\nTotal Signals: {total_signals}\nAvg WinRate: {df_res['WinRate'].mean():.1f}%\n\n🏆 *TOP 10:*\n```\n{top10}\n```"
print(msg)
send_telegram(msg)
