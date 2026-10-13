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

# NSE 1000 Tokens
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
        if turnover < 1000000: return None # 10L पेक्षा कमी असेल तर नको

        # === 1. EARLY BUY @ 640 - 10:00 वाला - NUCLEUS साठी ===
        # Condition: आधी VWAP खाली, आता VWAP वर + Green
        if prev['C'] < prev['VWAP'] and curr['C'] > curr['VWAP'] and curr['C'] > curr['O'] and curr['RSI'] >= 48 and vol_ratio >= 1.5:
            entry=curr['C']; sl=curr['VWAP']*0.995
            risk=entry-sl
            if 0<risk and risk/entry<=0.015:
                t1=entry+risk*2.5
                return f"🟢 <b>{name} EARLY BUY @ {entry:.1f}</b> {pct:+.1f}% Vol:{vol_ratio:.1f}x Rs:{turnover/100000:.0f}L RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} VWAP Break T1:{t1:.1f}"

        # === 2. STRONG BUY - 12:30 वाला 653 ===
        if vol_ratio >= 1.8 and curr['C']>curr['O'] and 55<=curr['RSI']<=80 and curr['C']>curr['EMA9'] and curr['EMA9']>curr['VWAP']:
            entry=curr['C']; sl=min(curr['L'], curr['VWAP']); risk=entry-sl
            if 0<risk and risk/entry<=0.015:
                t1=entry+risk*2.5
                return f"🟢 <b>{name} STRONG BUY @ {entry:.1f}</b> {pct:+.1f}% Vol:{vol_ratio:.1f}x Rs:{turnover/100000:.0f}L RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} T1:{t1:.1f} T2:Trail"

        # === 3. SELL दोन्ही ===
        if prev['C'] > prev['VWAP'] and curr['C'] < curr['VWAP'] and curr['C'] < curr['O'] and curr['RSI'] <= 52 and vol_ratio >= 1.5:
            entry=curr['C']; sl=curr['VWAP']*1.005
            risk=sl-entry
            if 0<risk:
                t1=entry-risk*2.5
                return f"🔴 <b>{name} EARLY SELL @ {entry:.1f}</b> {pct:+.1f}% Vol:{vol_ratio:.1f}x Rs:{turnover/100000:.0f}L RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} VWAP Break T1:{t1:.1f}"

        if vol_ratio >= 1.8 and curr['C']<curr['O'] and 20<=curr['RSI']<=48 and curr['C']<curr['EMA9'] and curr['EMA9']<curr['VWAP']:
            entry=curr['C']; sl=max(curr['H'], curr['VWAP']); risk=sl-entry
            if 0<risk and risk/entry<=0.015:
                t1=entry-risk*2.5
                return f"🔴 <b>{name} STRONG SELL @ {entry:.1f}</b> {pct:+.1f}% Vol:{vol_ratio:.1f}x Rs:{turnover/100000:.0f}L RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} T1:{t1:.1f} T2:Trail"

    except Exception as e:
        return None

results=[]
with ThreadPoolExecutor(max_workers=35) as ex:
    futures={ex.submit(scan,it):it for it in all_tokens}
    for f in as_completed(futures):
        r=f.result()
        if r: results.append(r)

if results:
    header=f"⚡️ <b>NSE ALL V15 {now.strftime('%H:%M:%S')}</b> {len(all_tokens)} Checked\nEARLY 640 | STRONG 653 | Vol 1.5x+\n\n"
    send_tele(header + "\n\n".join(results[:20]))
else:
    send_tele(f"⏳ {now.strftime('%H:%M')} No Setup - {len(all_tokens)} Checked")
