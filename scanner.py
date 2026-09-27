# FINAL NSE 5000 V3 - ALL CONDITIONS + NO SETUP FIX
import os, json, pandas as pd, requests, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

STATE_FILE="trades_state.json"
TOP_FOCUS=["JUBLINGREA","ULTRAMAR","TEXRAIL","CEWATER","PREMIERPOL","AEGISVOPAK","KLBRENG-B","SHANTIGEAR","XTRANET","SANGAMIND"]

def clean(s): return os.getenv(s,"").strip()
def send_tg(m):
    try:
        url=f"https://api.telegram.org/bot{clean('TELEGRAM_BOT_TOKEN')}/sendMessage"
        requests.post(url, json={"chat_id": clean('TELEGRAM_CHAT_ID'), "text": m, "parse_mode":"Markdown"}, timeout=20)
    except: pass

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE,'r') as f:
                st=json.load(f)
                if st.get("date")==datetime.now().strftime("%Y-%m-%d"): return st
    except: pass
    return {"date": datetime.now().strftime("%Y-%m-%d"), "trades": []}
def save_state(s):
    with open(STATE_FILE,'w') as f: json.dump(s,f,indent=2)

# Angel Login
obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

# NSE 5000 Load
inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype']=='EQ')]
tokens=nse[['token','symbol']].values.tolist()[:5000]
groups=[tokens[i:i+500] for i in range(0, len(tokens), 500)]

def calc_rsi(s,p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))
def supertrend(df,p=10,m=3):
    hl2=(df['h']+df['l'])/2; atr=(df['h']-df['l']).rolling(p).mean()
    up=hl2+m*atr; lo=hl2-m*atr
    st=pd.Series(0.0,index=df.index)
    for i in range(1,len(df)):
        st.iloc[i]=up.iloc[i] if df['c'].iloc[i]<=st.iloc[i-1] else lo.iloc[i]
    return st

def scan_one(item):
    token,sym=item
    try:
        d_data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_DAY","fromdate":(datetime.now()-timedelta(days=25)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not d_data or len(d_data['data'])<15: return None
        ddf=pd.DataFrame(d_data['data'],columns=['t','o','h','l','c','v'])
        prev_close=ddf.iloc[-2]['c']
        base10=ddf.iloc[-11:-1]
        high10=base10['h'].max(); avg10_vol=base10['v'].mean()
        low10=base10['l'].min()
        rng10=(high10-low10)/low10*100 if low10 else 0

        i_data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":datetime.now().strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not i_data or len(i_data['data'])<5: return None
        df=pd.DataFrame(i_data['data'],columns=['t','o','h','l','c','v'])
        df['ema9']=df['c'].ewm(span=9).mean(); df['ema15']=df['c'].ewm(span=15).mean(); df['ema20']=df['c'].ewm(span=20).mean()
        df['rsi']=calc_rsi(df['c']); df['st']=supertrend(df)
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
        ema12=df['c'].ewm(span=12).mean(); ema26=df['c'].ewm(span=26).mean()
        df['macd']=ema12-ema26; df['signal']=df['macd'].ewm(span=9).mean(); df['hist']=df['macd']-df['signal']

        c=df.iloc[-1]; c920=df.iloc[1]; open_price=df.iloc[0]['o']
        score=0; cond=[]

        gap=(open_price-prev_close)/prev_close*100
        if gap>=1.5: score+=1; cond.append(f"Gap{gap:.1f}%")
        if df.iloc[0]['v'] >= (avg10_vol/75)*2.5: score+=1; cond.append("Vol3X")
        if df['v'].iloc[-1] >= avg10_vol*1.5: score+=1; cond.append("Vol1.5X")
        if 2<=rng10<=6 and c['c']>high10*0.99: score+=1.5; cond.append(f"10D{rng10:.1f}%")
        ema_cross = df['ema9'].iloc[-2]<=df['ema15'].iloc[-2] and df['ema9'].iloc[-1]>df['ema15'].iloc[-1]
        body=abs(c['c']-c['o']); rng=c['h']-c['l'] if c['h']!=c['l'] else 1
        if ema_cross and c['rsi']>=50 and body/rng>=0.4: score+=1; cond.append(f"EMAx{int(c['rsi'])}")
        if c['c']>df['vwap'].iloc[-1]: score+=1; cond.append("VWAP")
        if c['c']>df['ema20'].iloc[-1]: score+=0.5
        if c['c']>df['st'].iloc[-1]: score+=0.5
        if c['hist']>0: score+=0.5
        if sym in TOP_FOCUS: score+=1.5; cond.append("TOP10")

        IST=timezone(timedelta(hours=5,minutes=30))
        hour=datetime.now(IST).hour
        need = 5 if hour < 11 else 3.5

        if score>=need:
            sl=min(c920['l'], c['l']); risk=c['c']-sl
            if risk<=0 or risk/c['c']>0.05: return None
            return (score, sym, c['c'], sl, c['c']+risk, c['c']+risk*2, "+".join(cond))
    except: return None

state=load_state()
IST=timezone(timedelta(hours=5,minutes=30))
now=datetime.now(IST)
active=len([t for t in state["trades"] if t["status"]=="ACTIVE"])
total=len(state["trades"])

if total>=6:
    send_tg(f"⛔ *आजचे 6 Trade पूर्ण* @ {now.strftime('%H:%M')}")
elif active>=2:
    send_tg(f"⏳ *2 Active आहेत* @ {now.strftime('%H:%M')}\n{', '.join([t['symbol'] for t in state['trades'] if t['status']=='ACTIVE'])} | Today {total}/6")
else:
    all_res=[]
    def scan_group(g):
        res=[]
        with ThreadPoolExecutor(max_workers=80) as ex:
            futs={ex.submit(scan_one,t):t for t in g}
            for f in as_completed(futs):
                r=f.result()
                if r: res.append(r)
        return res
    with ThreadPoolExecutor(max_workers=10) as gex:
        futs=[gex.submit(scan_group,g) for g in groups]
        for f in as_completed(futs): all_res.extend(f.result())

    if all_res:
        all_res=sorted(all_res, key=lambda x: x[0], reverse=True)
        to_take=all_res[:2-active]
        msg=f"⚡ *NSE 5000 FAST @ {now.strftime('%H:%M')}* | A:{active}/2 T:{total}/6\n\n"
        for sc,sym,entry,sl,tgt,tgt2,cond in to_take:
            trade={"symbol":sym,"entry":entry,"sl":sl,"tgt":tgt,"tgt2":tgt2,"time":now.strftime('%H:%M'),"status":"ACTIVE","pnl":0,"cond":cond}
            state["trades"].append(trade)
            msg+=f"✅ {len(state['trades'])}/6 S:{sc:.1f}\n🔥 {sym} @ {entry:.1f} | {cond}\nSL:{sl:.1f} T1:{tgt:.1f} T2:{tgt2:.1f}\n\n"
        save_state(state)
        send_tg(msg+f"📌 1:1 ला 50% Book")
    else:
        send_tg(f"😴 No Setup @ {now.strftime('%H:%M')} | Need {5 if now.hour<11 else 3.5} | A:{active}/2 T:{total}/6")
