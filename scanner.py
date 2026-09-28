import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime, timedelta, timezone
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
API_KEY=clean('ANGEL_API_KEY'); CLIENT_ID=clean('ANGEL_CLIENT_ID'); PWD=clean('ANGEL_PASSWORD'); TOTP_SECRET=clean('ANGEL_TOTP_SECRET')
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN'); TELE_CHAT=clean('TELEGRAM_CHAT_ID')
STATE_FILE="trades_state.json"

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

def send_tg(msg):
    try: requests.get(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", params={"chat_id":TELE_CHAT,"text":msg}, timeout=15)
    except: pass

IST = timezone(timedelta(hours=5, minutes=30))
ist_now = datetime.now(IST)

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f: master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

# === NSE 750 FULL ===
def get_nse_750():
    headers={"User-Agent":"Mozilla/5.0"}
    s=requests.Session()
    try: s.get("https://www.nseindia.com",headers=headers,timeout=5)
    except: pass
    all_syms={}
    # Large, Mid, Small Cap वेगळे
    for idx, cap in [("NIFTY 100","LARGE"),("NIFTY MIDCAP 150","MID"),("NIFTY SMALLCAP 250","SMALL"),("NIFTY 500","LARGE")]:
        try:
            url=f"https://www.nseindia.com/api/equity-stockIndices?index={idx.replace(' ','%20')}"
            r=s.get(url,headers=headers,timeout=10).json()
            if 'data' in r:
                for d in r['data']:
                    sym=d['symbol']
                    if d.get('lastPrice',0)>30 and d.get('lastPrice',0)<6000:
                        if sym not in all_syms:
                            all_syms[sym]=cap
        except: continue
    if len(all_syms)<100:
        return {s:"MID" for s in ["HAL","BEL","BDL","MAZDOCK","RVNL","IRFC","PFC","RECLTD","BHEL","SAIL","NHPC","POLYCAB","DIXON","KAYNES","BSE","CDSL","SUZLON","ZOMATO","IRCTC","IEX","MCX","TATAPOWER","BANKBARODA","PNB","CANBK","IDFCFIRSTB","COFORGE","LTTS","TATAELXSI","PERSISTENT","RELIANCE","TCS","INFY","HDFCBANK"]}
    return all_syms

def get_pat(df):
    if len(df)<4: return []
    c1=df.iloc[-2]; c=df.iloc[-1]
    pats=[]; body=abs(c['Close']-c['Open'])+1.0
    low=min(c['Open'],c['Close'])-c['Low']; up=c['High']-max(c['Open'],c['Close'])
    if low>body*1.8 and c['Close']>c['Open']: pats.append("HAMMER")
    if up>body*1.8 and c['Close']<c['Open']: pats.append("INV_HAMMER")
    vol_ok=c['Volume']>df['Volume'].iloc[-6:-1].mean()*0.95
    if c1['Close']<c1['Open'] and c['Close']>c['Open'] and c['Close']>c1['Open'] and vol_ok: pats.append("BULL_ENGULF")
    if c1['Close']>c1['Open'] and c['Close']<c['Open'] and c['Close']<c1['Open'] and vol_ok: pats.append("BEAR_ENGULF")
    return pats

def analyze(sym):
    try:
        token=token_map.get(sym)
        if not token: return None
        fdate=(ist_now-timedelta(days=3)).strftime("%Y-%m-%d %H:%M"); tdate=ist_now.strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":fdate,"todate":tdate})['data']
        df=pd.DataFrame(data,columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<40: return None
        ltp=df['Close'].iloc[-1]
        df['EMA9']=df['Close'].ewm(9).mean(); df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3; df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss)); df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2; tr=pd.concat([df['High']-df['Low'],(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); up=hl2+2.5*atr; st=-1 if df['Close'].iloc[-1]>up.iloc[-2] else 1
        c=df.iloc[-1]; c3h=df['High'].iloc[-4:-1].max(); c3l=df['Low'].iloc[-4:-1].min(); vavg=df['Volume'].iloc[-11:-1].mean()
        pats=get_pat(df)

        buy_score=sum([c['Close']>c3h, c['EMA9']>c['VWAP'], c['EMA15']>c['VWAP'], st<0, c['RSI']>48 and c['RSI']<75, df['MACD'].iloc[-1]>0, c['Volume']>vavg*0.9])
        sell_score=sum([c['Close']<c3l, c['EMA9']<c['VWAP'], c['EMA15']<c['VWAP'], st>0, c['RSI']<52 and c['RSI']>25, df['MACD'].iloc[-1]<0, c['Volume']>vavg*0.9])

        if buy_score>=5:
            sl=min(c3l, ltp*0.994) # 0.6% SL
            r=ltp-sl
            if r<ltp*0.0025: sl=ltp*0.994; r=ltp*0.006
            tier="STAR ⭐" if any(p in pats for p in ["HAMMER","BULL_ENGULF"]) else "GOOD"
            return {"type":"BUY","symbol":sym,"score":buy_score,"pattern":"+ ".join(pats) if pats else "5/7 VWAP BO","ltp":ltp,"sl":sl,"t1":ltp*1.01,"t2":ltp*1.02,"rank":buy_score+(2 if pats else 0),"tier":tier}
        if sell_score>=5:
            sl=max(c3h, ltp*1.006)
            r=sl-ltp
            if r<ltp*0.0025: sl=ltp*1.006; r=ltp*0.006
            tier="STAR ⭐" if any(p in pats for p in ["INV_HAMMER","BEAR_ENGULF"]) else "GOOD"
            return {"type":"SELL","symbol":sym,"score":sell_score,"pattern":"+ ".join(pats) if pats else "5/7 VWAP BD","ltp":ltp,"sl":sl,"t1":ltp*0.99,"t2":ltp*0.98,"rank":sell_score+(2 if pats else 0),"tier":tier}
    except: return None

# === STATE MANAGEMENT - 2 ACTIVE, 6 TOTAL ===
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f: return json.load(f)
    return {"date":ist_now.strftime("%Y-%m-%d"),"active":[],"closed":[],"total":0}

def save_state(st):
    with open(STATE_FILE,'w') as f: json.dump(st,f)

state=load_state()
if state['date']!=ist_now.strftime("%Y-%m-%d"):
    state={"date":ist_now.strftime("%Y-%m-%d"),"active":[],"closed":[],"total":0}

# 1. Active Trades चे Trailing Check
msg_trail=""
new_active=[]
for tr in state['active']:
    token=token_map.get(tr['symbol'])
    if not token: continue
    try:
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(ist_now-timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),"todate":ist_now.strftime("%Y-%m-%d %H:%M")})['data']
        ltp=data[-1][4]
        entry=tr['entry']
        if tr['type']=="BUY":
            profit_pct=(ltp/entry-1)*100
            if profit_pct>=1.0 and not tr.get('trailed'):
                # 1% वर 50% Trailing -> SL = Entry + 0.5%
                tr['sl']=entry*1.005
                tr['trailed']=True
                msg_trail+=f"🔄 TRAIL BUY {tr['symbol']} 1% Hit! SL-> {tr['sl']:.1f} (50% Trail)\n"
            if ltp<=tr['sl'] or ltp<=tr['t2'] or profit_pct<=-0.6:
                state['closed'].append({**tr,"exit":ltp,"pnl":profit_pct})
                msg_trail+=f"✅ CLOSED BUY {tr['symbol']} P/L {profit_pct:.2f}%\n"
                continue
        else:
            profit_pct=(1-ltp/entry)*100
            if profit_pct>=1.0 and not tr.get('trailed'):
                tr['sl']=entry*0.995
                tr['trailed']=True
                msg_trail+=f"🔄 TRAIL SELL {tr['symbol']} 1% Hit! SL-> {tr['sl']:.1f} (50% Trail)\n"
            if ltp>=tr['sl'] or ltp>=tr['t2'] or profit_pct<=-0.6:
                state['closed'].append({**tr,"exit":ltp,"pnl":profit_pct})
                msg_trail+=f"✅ CLOSED SELL {tr['symbol']} P/L {profit_pct:.2f}%\n"
                continue
        new_active.append(tr)
    except: new_active.append(tr)

state['active']=new_active

# 2. नवीन Signal - फक्त 6 Total आणि 2 Active
can_take = 6 - len(state['active']) - len(state['closed'])
can_take = min(can_take, 2 - len(state['active']))
msg_new=""
if can_take>0:
    nse750=get_nse_750()
    # Top Gainer/Loser मधूनच 750 मधून Scan
    headers={"User-Agent":"Mozilla/5.0"}; s=requests.Session()
    try: s.get("https://www.nseindia.com",headers=headers,timeout=5)
    except: pass
    gainers=[]; losers=[]
    for idx in ["NIFTY 100","NIFTY MIDCAP 150","NIFTY SMALLCAP 250"]:
        try:
            url=f"https://www.nseindia.com/api/equity-stockIndices?index={idx.replace(' ','%20')}"
            r=s.get(url,headers=headers,timeout=10).json()
            if 'data' in r:
                df=pd.DataFrame(r['data']).sort_values('pChange', ascending=False)
                gainers.extend([x for x in df.head(20)['symbol'] if x in nse750])
                losers.extend([x for x in df.tail(20)['symbol'] if x in nse750])
        except: continue

    candidates=[]
    for sym in gainers[:25]:
        if sym in [t['symbol'] for t in state['active']+state['closed']]: continue
        res=analyze(sym)
        if res and res['type']=="BUY": candidates.append((res,nse750.get(sym,"MID")))
    for sym in losers[:25]:
        if sym in [t['symbol'] for t in state['active']+state['closed']]: continue
        res=analyze(sym)
        if res and res['type']=="SELL": candidates.append((res,nse750.get(sym,"MID")))

    # LARGE 1 + MID 1 + SMALL 1 Balance
    candidates=sorted(candidates, key=lambda x: x[0]['rank'], reverse=True)
    picked=[]
    caps_taken=[]
    for res,cap in candidates:
        if len(picked)>=can_take: break
        if cap in caps_taken and len(candidates)>5: continue
        picked.append(res); caps_taken.append(cap)
        state['active'].append({"symbol":res['symbol'],"type":res['type'],"entry":res['ltp'],"sl":res['sl'],"t1":res['t1'],"t2":res['t2'],"trailed":False})
        state['total']+=1
        t1p=1.0
        msg_new+=f"{res['tier']} {res['type']} {res['symbol']} ({cap}) {res['score']}/7 {res['pattern']} E:{res['ltp']:.1f} SL:{res['sl']:.1f} T1:{res['t1']:.1f}(1%) T2:{res['t2']:.1f}(2%) Trail 50%\n"

save_state(state)

final_msg=f"🎯 INTRADAY 6 TRADE SYSTEM | {ist_now.strftime('%d %b %H:%M')} IST\nActive {len(state['active'])}/2 | Closed {len(state['closed'])}/6 | NSE 750 5Min\n"
if msg_trail: final_msg+=f"\n{msg_trail}\n"
if msg_new: final_msg+=f"🔥 NEW SIGNAL ({len(state['active'])} Active):\n{msg_new}\n"
else: final_msg+=f"No New Signal - {len(state['active'])} Active Running\n"

final_msg+=f"\nActive Trades:\n"
for t in state['active']:
    final_msg+=f"{t['type']} {t['symbol']} E:{t['entry']:.1f} SL:{t['sl']:.1f} {'TRAILED' if t.get('trailed') else ''}\n"

print(final_msg); send_tg(final_msg)
