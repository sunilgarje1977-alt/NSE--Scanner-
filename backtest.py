import os, pandas as pd, requests
from SmartApi import SmartConnect
import pyotp
from datetime import datetime, timedelta
from collections import Counter

def clean(s): return os.getenv(s,"").strip()
def send_telegram(msg):
    try:
        token=clean("TELEGRAM_BOT_TOKEN")
        chat=clean("TELEGRAM_CHAT_ID")
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id":chat,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

def get_history(token, days=30):
    end=datetime.now()
    start=end-timedelta(days=days)
    d=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":start.strftime('%Y-%m-%d 09:15'),"todate":end.strftime('%Y-%m-%d 15:30')})
    if not d or not d.get('data'): return pd.DataFrame()
    return pd.DataFrame(d['data'], columns=['t','o','h','l','c','v'])

df=get_history("2885",30)
if len(df)<30:
    send_telegram("❌ Backtest Failed: No Data")
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
for i in range(25,len(df)-10):
    r=df.iloc[i]; p=df.iloc[i-1]
    if r['v'] < r['vol10']*1.5: continue
    is_sell = p['ema9']>=p['ema15'] and r['ema9']<r['ema15'] and r['rsi']<=40 and r['c']<r['vwap'] and r['c']<r['o']
    is_buy = p['ema9']<=p['ema15'] and r['ema9']>r['ema15'] and r['rsi']>=60 and r['c']>r['vwap'] and r['c']>r['o']
    if not (is_sell or is_buy): continue
    entry=r['c']
    if is_sell:
        sl=r['h']; risk=abs(entry-sl); t1=entry-risk*1; t2=entry-risk*2.5
    else:
        sl=r['l']; risk=abs(entry-sl); t1=entry+risk*1; t2=entry+risk*2.5
    res="No Hit"
    for j in range(i+1, min(i+11,len(df))):
        f=df.iloc[j]
        if is_sell:
            if f['h']>=sl: res="SL"; break
            if f['l']<=t2: res="T2 WIN"; break
            if f['l']<=t1: res="T1 WIN"; break
        else:
            if f['l']<=sl: res="SL"; break
            if f['h']>=t2: res="T2 WIN"; break
            if f['h']>=t1: res="T1 WIN"; break
    trades.append(res)

c=Counter(trades)
total=len(trades)
wins=c['T1 WIN']+c['T2 WIN']
winrate = wins/total*100 if total>0 else 0

msg = f"""
📊 *NSE BACKTEST - RELIANCE - 30 DAYS*

Total Signals: {total}
✅ Wins: {wins}
❌ SL: {c['SL']}
⏸️ No Hit: {c['No Hit']}
🎯 WinRate: {winrate:.1f}%

Details: {dict(c)}
"""
print(msg)
send_telegram(msg)
