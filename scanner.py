import os, requests, pandas as pd
from SmartApi import SmartConnect
import pyotp
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

def clean(s): return os.getenv(s,"").strip()
def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{clean('TELEGRAM_BOT_TOKEN')}/sendMessage", json={"chat_id": clean('TELEGRAM_CHAT_ID'), "text": m, "parse_mode":"Markdown"}, timeout=15)
    except: pass

obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype'].isin(['EQ']))]
TOP_10 = ["ULTRAMAR","JUBLINGREA","CEWATER","FMCGIETF","PREMIERPOL","SHANTIGEAR","XTRANET","KLBRENG-B","MOBIKWIK","TEXRAIL"]
tokens=nse[['token','symbol']].values.tolist()[:1000]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    rs=g/l; return 100-(100/(1+rs))
def calc_vwap(df): return (df['c']*df['v']).cumsum()/df['v'].cumsum()

def check_10d_consolidation(token, direction="BUY"):
    try:
        daily = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_DAY","fromdate": (datetime.now()-timedelta(days=20)).strftime("%Y-%m-%d 09:15"), "todate": datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not daily or 'data' not in daily or not daily['data'] or len(daily['data']) < 12: return False, 0
        ddf = pd.DataFrame(daily['data'], columns=['t','o','h','l','c','v'])
        last10 = ddf.tail(10)
        high10 = last10['h'].max()
        low10 = last10['l'].min()
        range_pct = (high10 - low10) / low10 * 100 if low10>0 else 100
        # 10 Days Consolidation: Range < 15% - जास्त Tight
        if range_pct > 15: return False, range_pct
        
        curr_price = ddf.iloc[-1]['c']
        if direction == "BUY":
            is_bottom = curr_price <= low10 * 1.10  # Bottom 10% मध्ये
            return is_bottom, range_pct
        else:
            is_top = curr_price >= high10 * 0.90  # Top 10% मध्ये
            return is_top, range_pct
    except:
        return False, 0

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
        vol_ok = c['v'] >= avg10*1.5  # Volume Breakout/Breakdown
        body = abs(c['c']-c['o']); rng = c['h']-c['l'] if c['h']!=c['l'] else 1
        maru = body/rng >= 0.7
        engulf_buy = p['c']<p['o'] and c['c']>c['o'] and c['c']>p['o'] and c['o']<p['c']
        hammer = (c['l']<min(c['o'],c['c']) and (min(c['o'],c['c'])-c['l']) > body*1.5)
        engulf_sell = p['c']>p['o'] and c['c']<c['o'] and c['c']<p['o'] and c['o']>p['c']
        shoot = (c['h']>max(c['o'],c['c']) and (c['h']-max(c['o'],c['c'])) > body*1.5)
        ema_up = df['ema9'].iloc[-2] < df['ema15'].iloc[-2] and df['ema9'].iloc[-1] > df['ema15'].iloc[-1]
        ema_down = df['ema9'].iloc[-2] > df['ema15'].iloc[-2] and df['ema9'].iloc[-1] < df['ema15'].iloc[-1]
        
        # BUY: 10D Consolidation + Bottom + Volume Breakout + Full Logic
        if ema_up and c['rsi']>=60 and c['c']>c['vwap'] and vol_ok and (maru or engulf_buy or hammer) and c['c']>c['o']:
            ok, rng_pct = check_10d_consolidation(token, "BUY")
            if ok:
                sl=c['l']; risk=c['c']-sl
                if risk>0:
                    tgt=c['c']+risk*2.5
                    star="⭐" if any(x in sym for x in TOP_10) else ""
                    return f"🟢 BUY {star} {sym} @ {c['c']:.2f} SL:{sl:.2f} TGT:{tgt:.2f} [10D:{rng_pct:.1f}%+Bottom+Vol2x]"

        # SELL: 10D Consolidation + Top + Volume Breakdown + Full Logic
        if ema_down and c['rsi']<=40 and c['c']<c['vwap'] and vol_ok and (maru or engulf_sell or shoot) and c['c']<c['o']:
            ok, rng_pct = check_10d_consolidation(token, "SELL")
            if ok:
                sl=c['h']; risk=sl-c['c']
                if risk>0:
                    tgt=c['c']-risk*2.5
                    star="⭐" if any(x in sym for x in TOP_10) else ""
                    return f"🔴 SELL {star} {sym} @ {c['c']:.2f} SL:{sl:.2f} TGT:{tgt:.2f} [10D:{rng_pct:.1f}%+Top+Vol2x]"
        return None
    except: return None

IST = timezone(timedelta(hours=5, minutes=30))
now_ist=datetime.now(IST)
final=[]
with ThreadPoolExecutor(max_workers=50) as ex:
    futures={ex.submit(scan_one, t): t for t in tokens}
    for f in as_completed(futures):
        r=f.result()
        if r: final.append(r)
        if len(final)>=3: break

final=final[:3]
if final:
    msg=f"🚀 *NSE 1000 10D CONS BREAKOUT/BREAKDOWN | {now_ist.strftime('%H:%M')}*\n\n" + "\n\n".join(final)
    send_tg(msg); print(msg)
else:
    send_tg(f"😴 No 10D Breakout/Breakdown @ {now_ist.strftime('%H:%M')} | 1000 Scanned | Buy:Bottom | Sell:Top")
    print("No setup")
