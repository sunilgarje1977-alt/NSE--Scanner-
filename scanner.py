import os, requests, pandas as pd
from SmartApi import SmartConnect
import pyotp
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

def clean(s): return os.getenv(s,"").strip()
def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{clean('TELEGRAM_BOT_TOKEN')}/sendMessage", json={"chat_id": clean('TELEGRAM_CHAT_ID'), "text": m, "parse_mode":"Markdown"}, timeout=10)
    except: pass

obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype'].isin(['EQ']))]
tokens=nse[['token','symbol']].values.tolist()[:1000]
TOP_10 = ["ULTRAMAR","JUBLINGREA","CEWATER","FMCGIETF","PREMIERPOL","SHANTIGEAR","XTRANET","KLBRENG-B","MOBIKWIK","TEXRAIL"]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def calc_vwap(df): return (df['c']*df['v']).cumsum()/df['v'].cumsum()

def check_10d(token, curr_price):
    try:
        daily=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_DAY","fromdate":(datetime.now()-timedelta(days=20)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not daily or 'data' not in daily or len(daily['data'])<12: return None,0
        ddf=pd.DataFrame(daily['data'],columns=['t','o','h','l','c','v'])
        base=ddf.tail(11).head(10)
        high10=base['h'].max(); low10=base['l'].min()
        rng=(high10-low10)/low10*100 if low10>0 else 100
        if rng<3 or rng>5: return None,rng
        if curr_price>=high10*0.998: return "BUY",rng
        if curr_price<=low10*1.002: return "SELL",rng
        return None,rng
    except: return None,0

def scan_one(item):
    token,sym=item
    try:
        # 1MIN FAST
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_MINUTE","fromdate":datetime.now().strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not data or 'data' not in data or len(data['data'])<30: return None
        df=pd.DataFrame(data['data'],columns=['t','o','h','l','c','v'])
        df['ema9']=df['c'].ewm(span=9).mean(); df['ema15']=df['c'].ewm(span=15).mean(); df['rsi']=calc_rsi(df['c']); df['vwap']=calc_vwap(df)
        c=df.iloc[-1]; p=df.iloc[-2]
        # CROSS LOGIC
        ema9=df['ema9'].iloc[-1]; ema15=df['ema15'].iloc[-1]; ema9_pr=df['ema9'].iloc[-2]; ema15_pr=df['ema15'].iloc[-2]
        cross_up=ema9_pr<=ema15_pr and ema9>ema15 and c['c']>ema9
        cross_down=ema9_pr>=ema15_pr and ema9<ema15 and c['c']<ema9
        
        vol_ok=c['v']>=df['v'].tail(11).head(10).mean()*1.2
        body=abs(c['c']-c['o']); rng=c['h']-c['l'] if c['h']!=c['l'] else 1
        maru=body/rng>=0.6
        eng_buy=p['c']<p['o'] and c['c']>c['o'] and c['c']>p['o']
        eng_sell=p['c']>p['o'] and c['c']<c['o'] and c['c']<p['o']
        hammer=(c['l']<min(c['o'],c['c']) and (min(c['o'],c['c'])-c['l'])>body*1.2)
        shoot=(c['h']>max(c['o'],c['c']) and (c['h']-max(c['o'],c['c']))>body*1.2)

        sig,rng_pct=check_10d(token,c['c'])
        if not sig: return None
        star="⭐" if any(x in sym for x in TOP_10) else ""

        if sig=="BUY" and cross_up and c['rsi']>=58 and c['c']>c['vwap'] and vol_ok and (maru or eng_buy or hammer):
            sl=c['l']; risk=c['c']-sl
            if risk>0: return f"🟢 BUY {star} {sym} @ {c['c']:.2f} SL:{sl:.2f} TGT:{c['c']+risk*2.5:.2f} [1M+10D:{rng_pct:.1f}%]"

        if sig=="SELL" and cross_down and c['rsi']<=42 and c['c']<c['vwap'] and vol_ok and (maru or eng_sell or shoot):
            sl=c['h']; risk=sl-c['c']
            if risk>0: return f"🔴 SELL {star} {sym} @ {c['c']:.2f} SL:{sl:.2f} TGT:{c['c']-risk*2.5:.2f} [1M+10D:{rng_pct:.1f}%]"
    except: return None

IST=timezone(timedelta(hours=5,minutes=30))
now_ist=datetime.now(IST)
final=[]
# ULTRA FAST - 60 Workers
with ThreadPoolExecutor(max_workers=60) as ex:
    futs={ex.submit(scan_one,t):t for t in tokens}
    for f in as_completed(futs):
        r=f.result()
        if r: 
            final.append(r)
            if len(final)>=3: break

if final:
    msg=f"⚡ *NSE 1000 1MIN FAST | 10D 3-5% | {now_ist.strftime('%H:%M')}*\n\n" + "\n\n".join(final[:3])
    send_tg(msg); print(msg)
else:
    send_tg(f"😴 No 1MIN 3-5% Setup @ {now_ist.strftime('%H:%M')} | 1000 Scanned")
