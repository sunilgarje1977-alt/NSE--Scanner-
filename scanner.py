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
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"HTML"}, timeout=20)
    except: pass

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist)
today_str=now.strftime("%Y-%m-%d")
smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

# NSE ALL - 500 ची लिमिट काढली - SHRINGARMS सारखे Smallcap पण येतील
master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()
tokens_all = {}
for s in master:
    if s['exch_seg']=='NSE' and s['instrumenttype']=='' and s['symbol'].endswith('-EQ'):
        sym=s['symbol'].replace('-EQ','')
        tokens_all[sym]=s['token']

# Top 1000 घे - GitHub 2 मिनिटात 1800 करू शकत नाही
all_tokens = list(tokens_all.items())[:1000]
print(f"NSE ALL Tokens: {len(all_tokens)} - SHRINGARMS Included: {'SHRINGARMS' in tokens_all}")

def scan(item):
    name, token=item
    try:
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_MINUTE","fromdate":f"{today_str} 09:15","todate":f"{today_str} 15:30"})
        if not hist or 'data' not in hist or len(hist['data'])<30: return None
        df=pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V'])
        df['EMA9']=df['C'].ewm(span=9).mean()
        df['VWAP']=(df['V']*(df['H']+df['L']+df['C'])/3).cumsum()/df['V'].cumsum()
        df['VOLAVG']=df['V'].rolling(20).mean()
        d=df['C'].diff()
        df['RSI']=100-(100/(1+d.where(d>0,0).rolling(14).mean()/-d.where(d<0,0).rolling(14).mean().replace(0,0.01)))
        curr=df.iloc[-1]; first=df.iloc[0]
        pct=(curr['C']-first['O'])/first['O']*100
        vol_ratio=curr['V']/curr['VOLAVG'] if curr['VOLAVG']>0 else 0
        if vol_ratio < 1.2: return None # तुझीच Volume Condition
        if curr['C'] < 20: return None

        # 🟢 BUY - तुझ्या Chart वाली Condition - SHRINGARMS 12:31
        # Price 303 > VWAP 296 + RSI 59.75 + Green + Vol
        if curr['C']>curr['O'] and 55<=curr['RSI']<=80 and curr['C']>curr['EMA9'] and curr['EMA9']>curr['VWAP'] and curr['C']>curr['VWAP']:
            entry=curr['C']; sl=curr['VWAP'] if curr['VWAP']<entry else curr['L']
            risk=entry-sl
            if 0<risk and risk/entry<=0.02:
                t1=entry+risk*2.5
                return f"🟢 <b>{name} BUY</b> @ {entry:.1f} {pct:+.1f}% Vol:{vol_ratio:.1f}x RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} T1:{t1:.1f} (2.5x) T2:Trail"

        # 🔴 SELL - उलट Condition
        if curr['C']<curr['O'] and 20<=curr['RSI']<=45 and curr['C']<curr['EMA9'] and curr['EMA9']<curr['VWAP'] and curr['C']<curr['VWAP']:
            entry=curr['C']; sl=curr['VWAP'] if curr['VWAP']>entry else curr['H']
            risk=sl-entry
            if 0<risk and risk/entry<=0.02:
                t1=entry-risk*2.5
                return f"🔴 <b>{name} SELL</b> @ {entry:.1f} {pct:+.1f}% Vol:{vol_ratio:.1f}x RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} T1:{t1:.1f} (2.5x) T2:Trail"

    except: return None

results=[]
with ThreadPoolExecutor(max_workers=35) as ex:
    for f in as_completed({ex.submit(scan,it):it for it in all_tokens}):
        r=f.result()
        if r: results.append(r)

if results:
    send_tele(f"⚡️ <b>NSE ALL BUY/SELL {now.strftime('%H:%M:%S')}</b> {len(all_tokens)} Checked\n\n" + "\n\n".join(results[:15]))
else:
    send_tele(f"⏳ {now.strftime('%H:%M')} NSE ALL No Setup - {len(all_tokens)} Checked") 
