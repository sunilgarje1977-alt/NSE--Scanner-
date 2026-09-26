import os, pandas as pd
from SmartApi import SmartConnect
import pyotp
from datetime import datetime, timedelta
from collections import Counter

def clean(s):
    return os.getenv(s,"").strip()

obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

SYMBOL_TOKEN = "2885"
SYMBOL_NAME = "RELIANCE"

def get_history(days=30):
    end = datetime.now()
    start = end - timedelta(days=days)
    data = obj.getCandleData({
        "exchange":"NSE",
        "symboltoken":SYMBOL_TOKEN,
        "interval":"FIVE_MINUTE",
        "fromdate": start.strftime('%Y-%m-%d 09:15'),
        "todate": end.strftime('%Y-%m-%d 15:30')
    })
    if not data or not data.get('data'):
        return pd.DataFrame()
    return pd.DataFrame(data['data'], columns=['t','o','h','l','c','v'])

df = get_history(30)
if len(df) < 30:
    print("Data not found")
    exit()

df['ema9']=df['c'].ewm(span=9).mean()
df['ema15']=df['c'].ewm(span=15).mean()
df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
df['vol10']=df['v'].rolling(10).mean()
diff=df['c'].diff()
up=diff.where(diff>0,0).rolling(14).mean()
down=-diff.where(diff<0,0).rolling(14).mean()
df['rsi']=100-(100/(1+up/down))

trades=[]
for i in range(25, len(df)-10):
    row=df.iloc[i]
    prev=df.iloc[i-1]
    if row['v'] < row['vol10']*1.5:
        continue

    is_sell = prev['ema9']>=prev['ema15'] and row['ema9']<row['ema15'] and row['rsi']<=40 and row['c']<row['vwap'] and row['c']<row['o']
    is_buy = prev['ema9']<=prev['ema15'] and row['ema9']>row['ema15'] and row['rsi']>=60 and row['c']>row['vwap'] and row['c']>row['o']

    if not (is_sell or is_buy):
        continue

    entry=row['c']
    if is_sell:
        sl=row['h']
        risk=abs(entry-sl)
        tgt1=entry-risk*1
        tgt2=entry-risk*2.5
    else:
        sl=row['l']
        risk=abs(entry-sl)
        tgt1=entry+risk*1
        tgt2=entry+risk*2.5

    result="No Hit"
    for j in range(i+1, min(i+11, len(df))):
        f=df.iloc[j]
        if is_sell:
            if f['h']>=sl:
                result="SL"
                break
            if f['l']<=tgt2:
                result="T2 WIN"
                break
            if f['l']<=tgt1:
                result="T1 WIN"
                break
        else:
            if f['l']<=sl:
                result="SL"
                break
            if f['h']>=tgt2:
                result="T2 WIN"
                break
            if f['h']>=tgt1:
                result="T1 WIN"
                break
    trades.append(result)

c=Counter(trades)
total=len(trades)
wins=c['T1 WIN']+c['T2 WIN']
print(f"\n--- BACKTEST {SYMBOL_NAME} - 30 DAYS ---")
print(f"Total Signals: {total}")
print(f"Wins: {wins} | Loss (SL): {c['SL']} | No Hit: {c['No Hit']}")
if total>0:
    print(f"WinRate: {wins/total*100:.1f}%")
print(c)
