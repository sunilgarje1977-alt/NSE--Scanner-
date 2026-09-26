import os, requests, pandas as pd
from SmartApi import SmartConnect
import pyotp
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import pytz

def clean(s): return os.getenv(s,"").strip()
def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{clean('TELEGRAM_BOT_TOKEN')}/sendMessage", json={"chat_id": clean('TELEGRAM_CHAT_ID'), "text": m, "parse_mode":"Markdown"}, timeout=15)
    except: pass

# Angel Login
obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype'].isin(['EQ']))]
TOP_10 = ["ULTRAMAR", "TEXRAIL", "CEWATER", "AEGISVOPAK", "PREMIERPOL", "KLBRENG-B", "SANGAMIND", "SHANTIGEAR", "XTRANET", "MOBIKWIK"]
tokens=nse[['token','symbol']].values.tolist()[:1000]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    rs=g/l; return 100-(100/(1+rs))
def calc_vwap(df): return (df['c']*df['v']).cumsum()/df['v'].cumsum()

def scan_one(item):
    token,sym=item
    try:
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate": datetime.now().strftime("%Y-%m-%d 09:15"), "todate": datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not data or 'data' not in data or not data['data']: return None
        df=pd.DataFrame(data['data'], columns=['t','o','h','l','c','v'])
        if len(df)<30: return None
        df['ema9']=df['c'].ewm(span=9).mean(); df['ema15']=df['c'].ewm(span=15).mean(); df['rsi']=calc_rsi(df['c']); df['vwap']=calc_vwap(df)
        c=df.iloc[-1]; p=df.iloc[-2]
        avg10=df['v'].tail(11).head(10).mean()
        vol_ok = c['v'] >= avg10*1.5
        body = abs(c['c']-c['o']); rng = c['h']-c['l'] if c['h']!=c['l'] else 1
        maru = body/rng >= 0.7
        engulf_buy = p['c']<p['o'] and c['c']>c['o'] and c['c']>p['o'] and c['o']<p['c']
        hammer = (c['l']<min(c['o'],c['c']) and (min(c['o'],c['c'])-c['l']) > body*1.5)
        engulf_sell = p['c']>p['o'] and c['c']<c['o'] and c['c']<p['o'] and c['o']>p['c']
        shoot = (c['h']>max(c['o'],c['c']) and (c['h']-max(c['o'],c['c'])) > body*1.5)
        ema_up = df['ema9'].iloc[-2] < df['ema15'].iloc[-2] and df['ema9'].iloc[-1] > df['ema15'].iloc[-1]
        ema_down = df['ema9'].iloc[-2] > df['ema15'].iloc[-2] and df['ema9'].iloc[-1] < df['ema15'].iloc[-1]
        
        # FULL FILTER - एकही काढला नाही
        if ema_up and c['rsi']>=60 and c['c']>c['vwap'] and vol_ok and (maru or engulf_buy or hammer) and c['c']>c['o']:
            sl=c['l']; risk=c['c']-sl
            if risk>0:
                tgt=c['c']+risk*2.5
                star="⭐" if any(x in sym for x in TOP_10) else ""
                pat="Maru" if maru else "Engulf" if engulf_buy else "Hammer"
                return f"🟢 BUY {star} {sym} @ {c['c']:.2f} SL:{sl:.2f} TGT:{tgt:.2f} 1:2.5 {pat}+VWAP+Vol1.5x RSI:{c['rsi']:.0f}"
        if ema_down and c['rsi']<=40 and c['c']<c['vwap'] and vol_ok and (maru or engulf_sell or shoot) and c['c']<c['o']:
            sl=c['h']; risk=sl-c['c']
            if risk>0:
                tgt=c['c']-risk*2.5
                star="⭐" if any(x in sym for x in TOP_10) else ""
                pat="Maru" if maru else "Engulf" if engulf_sell else "Shoot"
                return f"🔴 SELL {star} {sym} @ {c['c']:.2f} SL:{sl:.2f} TGT:{tgt:.2f} 1:2.5 {pat}+VWAP+Vol1.5x RSI:{c['rsi']:.0f}"
        return None
    except: return None

ist=pytz.timezone('Asia/Kolkata'); now_ist=datetime.now(ist)
final=[]
with ThreadPoolExecutor(max_workers=100) as ex:
    futures={ex.submit(scan_one, t): t for t in tokens}
    for f in as_completed(futures):
        r=f.result()
        if r: final.append(r)
        if len(final)>=2: break

final=final[:2]
if final:
    msg=f"🚀 *NSE 1000 FAST FULL FILTER | {now_ist.strftime('%H:%M')}*\n\n" + "\n\n".join(final)
    send_tg(msg); print(msg)
else:
    # 9:30-11:30 च्या बाहेर असेल तरी Scan 1000 झाला हे दाखव
    send_tg(f"😴 No Strict Setup @ {now_ist.strftime('%H:%M')} | 1000 Scanned | FULL FILTER (EMA9x15+RSI60/40+VWAP+Vol1.5x+Maru/Engulf/Hammer) OK")
    print("No setup")
