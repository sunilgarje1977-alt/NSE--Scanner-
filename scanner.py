import os, requests, pyotp, pytz
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
API_KEY=os.getenv("ANGEL_API_KEY")
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID")
PASSWORD=os.getenv("ANGEL_PASSWORD")
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET")

def send_tele(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"HTML"}, timeout=20)
    except: pass

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist)
today_str=now.strftime("%Y-%m-%d")

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

# NSE 1000 List
master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
tokens_all = {}
for s in master:
    if s['exch_seg']=='NSE' and s['instrumenttype']=='' and s['symbol'].endswith('-EQ'):
        tokens_all[s['symbol'].replace('-EQ','')]=s['token']
all_tokens = list(tokens_all.items())[:1000]

def scan(item):
    name, token=item
    try:
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today_str} 09:15","todate":f"{today_str} 15:30"})
        if not hist or 'data' not in hist or len(hist['data'])<30: return None
        df=pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V'])
        df['EMA9']=df['C'].ewm(span=9).mean()
        df['VWAP']=(df['V']*(df['H']+df['L']+df['C'])/3).cumsum()/df['V'].cumsum()
        df['VOLAVG']=df['V'].rolling(20).mean()
        d=df['C'].diff()
        up=d.where(d>0,0).rolling(14).mean()
        down=-d.where(d<0,0).rolling(14).mean()
        df['RSI']=100-(100/(1+up/down.replace(0,0.01)))

        curr=df.iloc[-1]; prev=df.iloc[-2]; first=df.iloc[0]
        pct=(curr['C']-first['O'])/first['O']*100
        vol_ratio=curr['V']/curr['VOLAVG'] if curr['VOLAVG']>0 else 0
        turnover=curr['V']*curr['C']

        if curr['C'] < 50: return None
        if turnover < 1200000: return None
        if vol_ratio < 1.8: return None

        cross_up = prev['EMA9'] < prev['VWAP'] and curr['EMA9'] > curr['VWAP']
        cross_down = prev['EMA9'] > prev['VWAP'] and curr['EMA9'] < curr['VWAP']

        # BUY - RSI 60 Match
        if cross_up and curr['C'] > curr['EMA9'] and curr['C'] > curr['O'] and 60 <= curr['RSI'] <= 78:
            entry=curr['C']
            sl = max(curr['EMA9']*0.998, curr['L']*0.998)
            if sl < entry*0.992: sl = entry*0.992
            risk=entry-sl
            if 0<risk and risk/entry <= 0.01:
                t1=entry+risk*2.5
                return f"🟢 <b>{name} BUY @ {entry:.1f}</b> {pct:+.1f}% Vol:{vol_ratio:.1f}x RSI:{int(curr['RSI'])} Rs:{turnover/100000:.0f}L {now.strftime('%H:%M')}\nSL:{sl:.1f} (9EMA) T1:{t1:.1f} T2:Trail"

        # SELL - RSI 40 Match
        if cross_down and curr['C'] < curr['EMA9'] and curr['C'] < curr['O'] and 22 <= curr['RSI'] <= 40:
            entry=curr['C']
            sl = min(curr['EMA9']*1.002, curr['H']*1.002)
            if sl > entry*1.008: sl = entry*1.008
            risk=sl-entry
            if 0<risk and risk/entry <= 0.01:
                t1=entry-risk*2.5
                return f"🔴 <b>{name} SELL @ {entry:.1f}</b> {pct:+.1f}% Vol:{vol_ratio:.1f}x RSI:{int(curr['RSI'])} Rs:{turnover/100000:.0f}L {now.strftime('%H:%M')}\nSL:{sl:.1f} (9EMA) T1:{t1:.1f} T2:Trail"

    except: return None

results=[]
with ThreadPoolExecutor(max_workers=35) as ex:
    for f in as_completed({ex.submit(scan,it):it for it in all_tokens}):
        r=f.result()
        if r: results.append(r)

if results:
    header=f"⚡️ <b>NSE V18 {now.strftime('%H:%M:%S')}</b> {len(all_tokens)} Checked\n9EMAxVWAP | Vol 1.8x | RSI 60/40 | 12L Min\n\n"
    send_tele(header + "\n\n".join(results[:15]))
else:
    send_tele(f"⏳ {now.strftime('%H:%M')} No Setup (RSI 60 + Vol 1.8x Not Matched) - {len(all_tokens)} Checked")  
