# FILE: scanner.py - FINAL COMBO (Gap + Vol 5X + 10D 3-5% + EMA Cross)
import os, pandas as pd, requests, pyotp
from SmartApi import SmartConnect
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

def clean(s): return os.getenv(s,"").strip()
def send_tg(m):
    try:
        url=f"https://api.telegram.org/bot{clean('TELEGRAM_BOT_TOKEN')}/sendMessage"
        requests.post(url, json={"chat_id": clean('TELEGRAM_CHAT_ID'), "text": m, "parse_mode":"Markdown"}, timeout=15)
        print(m)
    except Exception as e: print(e)

obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype'].isin(['EQ']))]
tokens=nse[['token','symbol']].values.tolist()[:1000]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def combo_scan(item):
    token,sym=item
    score=0; reasons=[]
    try:
        daily=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_DAY","fromdate":(datetime.now()-timedelta(days=20)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not daily or 'data' not in daily or len(daily['data'])<12: return None
        ddf=pd.DataFrame(daily['data'],columns=['t','o','h','l','c','v'])
        prev_close=ddf.iloc[-2]['c']
        avg_5d_vol=ddf.tail(5)['v'].mean()

        intra=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":datetime.now().strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not intra or 'data' not in intra or len(intra['data'])<1: return None
        df=pd.DataFrame(intra['data'],columns=['t','o','h','l','c','v'])
        df['ema9']=df['c'].ewm(span=9).mean(); df['ema15']=df['c'].ewm(span=15).mean(); df['rsi']=calc_rsi(df['c'])
        c=df.iloc[-1]
        open_price=df.iloc[0]['o']

        gap=(open_price-prev_close)/prev_close*100
        if gap>=2: score+=1; reasons.append(f"Gap+{gap:.1f}%")

        avg_5min_vol=avg_5d_vol/75 if avg_5d_vol>0 else 0
        first_vol=df.iloc[0]['v']
        if avg_5min_vol>0 and first_vol >= avg_5min_vol*3:
            score+=1; reasons.append(f"Vol{first_vol/avg_5min_vol:.1f}X")

        base=ddf.iloc[-11:-1]
        high10=base['h'].max(); low10=base['l'].min()
        rng10=(high10-low10)/low10*100
        breakout = c['c'] > high10
        if 3 <= rng10 <= 5 and breakout:
            score+=2; reasons.append(f"10D{rng10:.1f}% BO")

        ema_cross_up = len(df)>=2 and df['ema9'].iloc[-2] <= df['ema15'].iloc[-2] and df['ema9'].iloc[-1] > df['ema15'].iloc[-1]
        body=abs(c['c']-c['o']); rng_c=c['h']-c['l'] if c['h']!=c['l'] else 1
        maru=body/rng_c>=0.5
        if ema_cross_up and c['rsi']>=55 and maru:
            score+=1; reasons.append(f"EMAx RSI{int(c['rsi'])}")

        if score>=2:
            sl=c['l']; risk=c['c']-sl if c['c']>sl else 0
            if risk<=0: return None
            stars="⭐"*score
            if score>=4: stars="🔥🔥🔥 JACKPOT"
            return (score, f"{stars} {sym} @ {c['c']:.2f} | {' + '.join(reasons)} | SL:{sl:.2f} TGT:{c['c']+risk*2.5:.2f} | Score:{score}/5")
    except: return None

IST=timezone(timedelta(hours=5,minutes=30))
now=datetime.now(IST)

final=[]
with ThreadPoolExecutor(max_workers=50) as ex:
    futs={ex.submit(combo_scan,t):t for t in tokens}
    for f in as_completed(futs):
        r=f.result()
        if r: final.append(r)

if final:
    final=sorted(final, key=lambda x: x[0], reverse=True)[:5]
    msgs=[x[1] for x in final]
    msg=f"⚡ *NSE 1000 COMBO @ {now.strftime('%H:%M')}* Gap+Vol+10D+EMA\n\n" + "\n\n".join(msgs)
    msg+=f"\n\n⚠️ Limit Order | SL-L | 9:45 Book | मोठी Candle Avoid"
    send_tg(msg)
else:
    if now.hour<9 or now.hour>=16:
        send_tg(f"⏰ Market बंद {now.strftime('%H:%M')} - उद्या 9:08/9:20/10:30 ला Run होईल")
    else:
        send_tg(f"😴 No Combo Setup @ {now.strftime('%H:%M')} | Score>=2 नाही")
