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

def get_top_movers():
    headers={"User-Agent":"Mozilla/5.0"}
    s=requests.Session()
    try: s.get("https://www.nseindia.com",headers=headers,timeout=5)
    except: pass
    gainers=[]; losers=[]
    for idx in ["NIFTY 100","NIFTY MIDCAP 150","NIFTY SMALLCAP 250"]:
        try:
            r=s.get(f"https://www.nseindia.com/api/equity-stockIndices?index={idx.replace(' ','%20')}",headers=headers,timeout=10).json()
            if 'data' in r:
                df=pd.DataFrame(r['data'])
                df=df[df['lastPrice']>30]
                df=df.sort_values('pChange',ascending=False)
                gainers.extend(df.head(15)['symbol'].tolist())
                losers.extend(df.tail(15)['symbol'].tolist())
        except: continue
    if not gainers:
        gainers=["KAYNES","POLYCAB","DIXON","BSE","CDSL","HAL","BEL","BHEL","RVNL","PFC","RECLTD","ZOMATO","TITAN","MARUTI","RELIANCE","TCS","INFY","COFORGE","LTTS","MCX"]
        losers=["BANKBARODA","PNB","CANBK","IDFCFIRSTB","SUZLON","YESBANK","IEX","TATAPOWER","IRFC","NHPC","SAIL","NTPC","TATAELXSI","IDEA","BHEL","RVNL","COFORGE","BANKBARODA","PNB","CANBK"]
    return list(dict.fromkeys(gainers))[:35], list(dict.fromkeys(losers))[:35]

def analyze(sym, side):
    try:
        token=token_map.get(sym)
        if not token: return None
        fdate=(ist_now-timedelta(days=3)).strftime("%Y-%m-%d %H:%M"); tdate=ist_now.strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":fdate,"todate":tdate})['data']
        df=pd.DataFrame(data,columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<30: return None
        ltp=df['Close'].iloc[-1]
        if ltp<30 or ltp>9000: return None

        # === INDICATORS ===
        df['EMA9']=df['Close'].ewm(9).mean()
        df['EMA15']=df['Close'].ewm(15).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2; tr=pd.concat([df['High']-df['Low'],(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); upper=hl2+2.0*atr; lower=hl2-2.0*atr
        # Supertrend
        st=-1 if df['Close'].iloc[-1]>upper.iloc[-2] else 1

        c=df.iloc[-1]; c1=df.iloc[-2]
        vavg=df['Volume'].iloc[-11:-1].mean()
        c3h=df['High'].iloc[-4:-1].max(); c3l=df['Low'].iloc[-4:-1].min()

        # Pattern
        pat=""; body=abs(c['Close']-c['Open'])+0.1
        low_wick=min(c['Open'],c['Close'])-c['Low']; up_wick=c['High']-max(c['Open'],c['Close'])
        if low_wick>body*1.5 and c['Close']>c['Open']: pat="HAMMER"
        elif up_wick>body*1.5 and c['Close']<c['Open']: pat="INV_HAMMER"
        elif c1['Close']<c1['Open'] and c['Close']>c['Open'] and c['Close']>c1['Open'] and c['Open']<c1['Close']: pat="BULL_ENGULF"
        elif c1['Close']>c1['Open'] and c['Close']<c['Open'] and c['Close']<c1['Open'] and c['Open']>c1['Close']: pat="BEAR_ENGULF"

        # 9EMA x 15EMA Cross
        ema_cross_up = df['EMA9'].iloc[-1] > df['EMA15'].iloc[-1]
        ema_cross_down = df['EMA9'].iloc[-1] < df['EMA15'].iloc[-1]
        fresh_cross_up = df['EMA9'].iloc[-2] <= df['EMA15'].iloc[-2] and df['EMA9'].iloc[-1] > df['EMA15'].iloc[-1]
        fresh_cross_down = df['EMA9'].iloc[-2] >= df['EMA15'].iloc[-2] and df['EMA9'].iloc[-1] < df['EMA15'].iloc[-1]

        # === BUY CONDITION 8 ===
        # 1:3C BO 2:EMA9>VWAP 3:EMA15>VWAP 4:9x15 Cross UP 5:ST Green 6:RSI 45-75 7:MACD>0 8:Vol
        buy_score=0; buy_cond=[]
        if c['Close']>c3h: buy_score+=1; buy_cond.append("3CBO")
        if c['EMA9']>c['VWAP']: buy_score+=1; buy_cond.append("E9>V")
        if df['EMA15'].iloc[-1]>c['VWAP']: buy_score+=1; buy_cond.append("E15>V")
        if ema_cross_up: buy_score+=1; buy_cond.append("9x15UP" + ("*" if fresh_cross_up else ""))
        if st<0: buy_score+=1; buy_cond.append("ST_G")
        if c['RSI']>45 and c['RSI']<78: buy_score+=1; buy_cond.append(f"RSI{c['RSI']:.0f}")
        if df['MACD'].iloc[-1]>0: buy_score+=1; buy_cond.append("MACD+")
        if c['Volume']>vavg*0.7: buy_score+=1; buy_cond.append("VOL")

        # === SELL CONDITION 8 ===
        sell_score=0; sell_cond=[]
        if c['Close']<c3l: sell_score+=1; sell_cond.append("3CBD")
        if c['EMA9']<c['VWAP']: sell_score+=1; sell_cond.append("E9<V")
        if df['EMA15'].iloc[-1]<c['VWAP']: sell_score+=1; sell_cond.append("E15<V")
        if ema_cross_down: sell_score+=1; sell_cond.append("9x15DN" + ("*" if fresh_cross_down else ""))
        if st>0: sell_score+=1; sell_cond.append("ST_R")
        if c['RSI']<55 and c['RSI']>22: sell_score+=1; sell_cond.append(f"RSI{c['RSI']:.0f}")
        if df['MACD'].iloc[-1]<0: sell_score+=1; sell_cond.append("MACD-")
        if c['Volume']>vavg*0.7: sell_score+=1; sell_cond.append("VOL")

        if side=="BUY" and buy_score>=5:
            sl=ltp*0.994
            return {"type":"BUY","symbol":sym,"score":buy_score,"cond":",".join(buy_cond),"pat":pat or "9x15 CROSS","ltp":ltp,"sl":sl,"t1":ltp*1.01,"t2":ltp*1.02,"rank":buy_score+(2 if pat else 0)+(1 if fresh_cross_up else 0),"tier":"STAR ⭐" if pat and fresh_cross_up else "GOOD","fresh":fresh_cross_up}
        if side=="SELL" and sell_score>=5:
            sl=ltp*1.006
            return {"type":"SELL","symbol":sym,"score":sell_score,"cond":",".join(sell_cond),"pat":pat or "9x15 CROSS","ltp":ltp,"sl":sl,"t1":ltp*0.99,"t2":ltp*0.98,"rank":sell_score+(2 if pat else 0)+(1 if fresh_cross_down else 0),"tier":"STAR ⭐" if pat and fresh_cross_down else "GOOD","fresh":fresh_cross_down}
    except Exception as e: return None

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f: st=json.load(f)
            if st.get('date')!=ist_now.strftime("%Y-%m-%d"):
                return {"date":ist_now.strftime("%Y-%m-%d"),"active":[],"closed":[],"pending":[]}
            if "pending" not in st: st["pending"]=[]
            if "closed" not in st: st["closed"]=[]
            if "active" not in st: st["active"]=[]
            return st
        except: pass
    return {"date":ist_now.strftime("%Y-%m-%d"),"active":[],"closed":[],"pending":[]}

state=load_state()

# === TRAILING + CLOSE CHECK ===
new_active=[]; trail_msg=""
for tr in state['active']:
    try:
        token=token_map.get(tr['symbol']);
        if not token: continue
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(ist_now-timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),"todate":ist_now.strftime("%Y-%m-%d %H:%M")})['data']
        ltp=data[-1][4]
        if tr['type']=="BUY":
            pct=(ltp/tr['entry']-1)*100
            if pct>=1.0 and not tr.get('trailed'): tr['sl']=tr['entry']*1.005; tr['trailed']=True; trail_msg+=f"🔄 TRAIL BUY {tr['symbol']} 1% Hit SL->{tr['sl']:.1f} ({pct:.1f}%)\n"
            if ltp<=tr['sl'] or pct>=2.0 or pct<=-0.6:
                state['closed'].append({**tr,"exit":ltp,"pnl":pct}); trail_msg+=f"✅ CLOSED BUY {tr['symbol']} {pct:.2f}% LTP:{ltp:.1f}\n"; continue
        else:
            pct=(1-ltp/tr['entry'])*100
            if pct>=1.0 and not tr.get('trailed'): tr['sl']=tr['entry']*0.995; tr['trailed']=True; trail_msg+=f"🔄 TRAIL SELL {tr['symbol']} 1% Hit SL->{tr['sl']:.1f} ({pct:.1f}%)\n"
            if ltp>=tr['sl'] or pct>=2.0 or pct<=-0.6:
                state['closed'].append({**tr,"exit":ltp,"pnl":pct}); trail_msg+=f"✅ CLOSED SELL {tr['symbol']} {pct:.2f}% LTP:{ltp:.1f}\n"; continue
        new_active.append(tr)
    except: new_active.append(tr)
state['active']=new_active

# === SCAN ===
gainers, losers = get_top_movers()
buys=[]; sells=[]
for sym in gainers:
    r=analyze(sym,"BUY")
    if r: buys.append(r)
for sym in losers:
    r=analyze(sym,"SELL")
    if r: sells.append(r)

buys=sorted(buys,key=lambda x:x['rank'],reverse=True)
sells=sorted(sells,key=lambda x:x['rank'],reverse=True)

# BUY 3 + SELL 3 Top
top_buys=buys[:3]; top_sells=sells[:3]
all_new = top_buys + top_sells

# Pending Queue Add
for r in all_new:
    if r['symbol'] not in [t['symbol'] for t in state['active']] and r['symbol'] not in [p['symbol'] for p in state['pending']] and r['symbol'] not in [c['symbol'] for c in state['closed']]:
        state['pending'].append(r)

# Sort pending by rank
state['pending']=sorted(state['pending'],key=lambda x:x['rank'],reverse=True)

# Active 2 Logic - One Close Second Active
can_take = 2 - len(state['active'])
total_left = 6 - len(state['active']) - len(state['closed'])
can_take = min(can_take, total_left)
if can_take<0: can_take=0

picked=[]
for i in range(can_take):
    if state['pending']:
        r=state['pending'].pop(0)
        state['active'].append({"symbol":r['symbol'],"type":r['type'],"entry":r['ltp'],"sl":r['sl'],"t1":r['t1'],"t2":r['t2'],"trailed":False})
        picked.append(r)

with open(STATE_FILE,'w') as f: json.dump(state,f)

# === TELEGRAM MSG ===
msg=f"🎯 INTRADAY 6 TRADE | {ist_now.strftime('%d %b %H:%M')} IST | 5Min Candle\nActive {len(state['active'])}/2 | Closed {len(state['closed'])}/6 | Pending {len(state['pending'])} | Scan {len(gainers)+len(losers)}\n"
if trail_msg: msg+=f"\n{trail_msg}\n"
if picked:
    msg+=f"🔥 NEW {len(picked)} ACTIVE (BUY {len([p for p in picked if p['type']=='BUY'])} + SELL {len([p for p in picked if p['type']=='SELL'])}):\n"
    for r in picked:
        msg+=f"{r['tier']} {r['type']} {r['symbol']} {r['score']}/8 {r['pat']} {r['cond']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f}(1%) T2:{r['t2']:.1f}(2%)\n"
else:
    if state['pending']:
        msg+=f"No New - Active Full 2/2\n"
    else:
        tb=f"{buys[0]['symbol']} {buys[0]['score']}/8" if buys else "None"
        ts=f"{sells[0]['symbol']} {sells[0]['score']}/8" if sells else "None"
        msg+=f"No Setup Now - Top BUY:{tb} SELL:{ts} - Next 5Min\n"

msg+=f"\n📈 Active Trades:\n"
for t in state['active']: msg+=f"{t['type']} {t['symbol']} E:{t['entry']:.1f} SL:{t['sl']:.1f} {'TRAILED' if t.get('trailed') else ''}\n"
if state['pending']:
    msg+=f"\n⏳ Pending Queue (One Close -> Next Active):\n"
    for p in state['pending'][:4]: msg+=f"{p['type']} {p['symbol']} {p['score']}/8 {p['pat']}\n"
if state['closed']:
    msg+=f"\n✅ Closed Today {len(state['closed'])}:\n"
    for c in state['closed'][-3:]: msg+=f"{c['type']} {c['symbol']} {c.get('pnl',0):.2f}%\n"

print(msg); send_tg(msg)
