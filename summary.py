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

def get_nse_750():
    headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"}
    s=requests.Session()
    s.headers.update(headers)
    try: s.get("https://www.nseindia.com",timeout=5)
    except: pass
    syms=[]
    for idx in ["NIFTY 100","NIFTY MIDCAP 150","NIFTY SMALLCAP 250"]:
        try:
            r=s.get(f"https://www.nseindia.com/api/equity-stockIndices?index={idx.replace(' ','%20')}",timeout=10).json()
            if 'data' in r:
                df=pd.DataFrame(r['data'])
                df=df[df['lastPrice']>30]
                syms.extend(df.sort_values('pChange',ascending=False).head(30)['symbol'].tolist())
                syms.extend(df.sort_values('pChange',ascending=False).tail(30)['symbol'].tolist())
        except: continue
    if len(syms)<20:
        syms=["KAYNES","POLYCAB","DIXON","BSE","CDSL","HAL","BEL","BHEL","RVNL","PFC","RECLTD","BANKBARODA","PNB","CANBK","IDFCFIRSTB","SUZLON","IDEA","YESBANK","IEX","MCX","COFORGE","LTTS","TATAELXSI","RVNL","TATAPOWER","IRFC","NHPC","SAIL","NTPC","RELIANCE","TCS","INFY","MARUTI","TITAN","ZOMATO"]
    return list(set(syms))[:80]

def analyze(sym, mode_hint):
    try:
        token=token_map.get(sym)
        if not token: return None
        fdate=(ist_now-timedelta(days=3)).strftime("%Y-%m-%d %H:%M"); tdate=ist_now.strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":fdate,"todate":tdate})['data']
        df=pd.DataFrame(data,columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<30: return None
        ltp=df['Close'].iloc[-1]
        df['EMA9']=df['Close'].ewm(9).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss)); df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2; tr=pd.concat([df['High']-df['Low'],(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); up=hl2+2.2*atr; st=-1 if df['Close'].iloc[-1]>up.iloc[-2] else 1
        c=df.iloc[-1]; vavg=df['Volume'].iloc[-11:-1].mean()
        c3h=df['High'].iloc[-4:-1].max(); c3l=df['Low'].iloc[-4:-1].min()

        # Pattern
        c1=df.iloc[-2]; body=abs(c['Close']-c['Open'])+1
        low_p=min(c['Open'],c['Close'])-c['Low']; up_p=c['High']-max(c['Open'],c['Close'])
        pat=""
        if low_p>body*1.5 and c['Close']>c['Open']: pat="HAMMER"
        if up_p>body*1.5 and c['Close']<c['Open']: pat="INV_HAMMER"
        if c1['Close']<c1['Open'] and c['Close']>c['Open'] and c['Close']>c1['Open']: pat="BULL_ENGULF"
        if c1['Close']>c1['Open'] and c['Close']<c['Open'] and c['Close']<c1['Open']: pat="BEAR_ENGULF"

        # === 4/7 वरच Signal - लवकर येईल ===
        buy_score=sum([c['Close']>df['EMA9'].iloc[-1], c['EMA9'].iloc[-1]>c['VWAP'], st<0, c['RSI']>45, df['MACD'].iloc[-1]>0, c['Volume']>vavg*0.8])
        sell_score=sum([c['Close']<df['EMA9'].iloc[-1], c['EMA9'].iloc[-1]<c['VWAP'], st>0, c['RSI']<55, df['MACD'].iloc[-1]<0, c['Volume']>vavg*0.8])

        if mode_hint=="BUY" and buy_score>=4:
            sl=ltp*0.994; r=ltp*0.006
            return {"type":"BUY","symbol":sym,"score":buy_score,"pat":pat if pat else "VWAP BO","ltp":ltp,"sl":sl,"t1":ltp*1.01,"t2":ltp*1.02,"rank":buy_score+(2 if pat else 0),"tier":"STAR ⭐" if pat else "GOOD"}
        if mode_hint=="SELL" and sell_score>=4:
            sl=ltp*1.006; r=ltp*0.006
            return {"type":"SELL","symbol":sym,"score":sell_score,"pat":pat if pat else "VWAP BD","ltp":ltp,"sl":sl,"t1":ltp*0.99,"t2":ltp*0.98,"rank":sell_score+(2 if pat else 0),"tier":"STAR ⭐" if pat else "GOOD"}
    except: return None

# State
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f: st=json.load(f)
            if st['date']!=ist_now.strftime("%Y-%m-%d"): return {"date":ist_now.strftime("%Y-%m-%d"),"active":[],"closed":[],"total":0}
            return st
        except: pass
    return {"date":ist_now.strftime("%Y-%m-%d"),"active":[],"closed":[],"total":0}

state=load_state()
# Active Trailing Check
new_active=[]; trail_msg=""
for tr in state['active']:
    token=token_map.get(tr['symbol'])
    if not token: continue
    try:
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(ist_now-timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"),"todate":ist_now.strftime("%Y-%m-%d %H:%M")})['data']
        ltp=data[-1][4]
        entry=tr['entry']
        if tr['type']=="BUY":
            pct=(ltp/entry-1)*100
            if pct>=1.0 and not tr.get('trailed'):
                tr['sl']=entry*1.005; tr['trailed']=True
                trail_msg+=f"🔄 TRAIL BUY {tr['symbol']} 1% Hit SL->{tr['sl']:.1f}\n"
            if ltp<=tr['sl'] or pct>=2.0 or pct<=-0.6:
                state['closed'].append({**tr,"exit":ltp,"pnl":pct}); trail_msg+=f"✅ CLOSED BUY {tr['symbol']} {pct:.2f}%\n"; continue
        else:
            pct=(1-ltp/entry)*100
            if pct>=1.0 and not tr.get('trailed'):
                tr['sl']=entry*0.995; tr['trailed']=True
                trail_msg+=f"🔄 TRAIL SELL {tr['symbol']} 1% Hit SL->{tr['sl']:.1f}\n"
            if ltp>=tr['sl'] or pct>=2.0 or pct<=-0.6:
                state['closed'].append({**tr,"exit":ltp,"pnl":pct}); trail_msg+=f"✅ CLOSED SELL {tr['symbol']} {pct:.2f}%\n"; continue
        new_active.append(tr)
    except: new_active.append(tr)
state['active']=new_active

# New Signal - RESET केला तर Block नाही
universe=get_nse_750()
buys=[]; sells=[]
for sym in universe:
    if sym in [t['symbol'] for t in state['active']]: continue
    # दोन्ही Check
    b=analyze(sym,"BUY")
    if b: buys.append(b)
    s=analyze(sym,"SELL")
    if s: sells.append(s)

buys=sorted(buys,key=lambda x:x['rank'],reverse=True)[:3]
sells=sorted(sells,key=lambda x:x['rank'],reverse=True)[:3]

# 2 Active Limit
can_take = min(2-len(state['active']), 6-len(state['active'])-len(state['closed']))
if can_take<0: can_take=0

picked=[]
if can_take>0:
    # LARGE+MID+SMALL Balance नको - जे Best आहे ते घे - Signal येणारच!
    combined = buys + sells
    combined = sorted(combined, key=lambda x: x['rank'], reverse=True)[:can_take]
    for r in combined:
        state['active'].append({"symbol":r['symbol'],"type":r['type'],"entry":r['ltp'],"sl":r['sl'],"t1":r['t1'],"t2":r['t2'],"trailed":False})
        picked.append(r)

with open(STATE_FILE,'w') as f: json.dump(state,f)

msg=f"🎯 INTRADAY 6 TRADE | {ist_now.strftime('%d %b %H:%M')} IST\nActive {len(state['active'])}/2 | Closed {len(state['closed'])}/6 | Scan {len(universe)} | NSE 750 5Min\n"
if trail_msg: msg+=f"\n{trail_msg}\n"
if picked:
    msg+=f"🔥 NEW {len(picked)} SIGNAL:\n"
    for r in picked:
        msg+=f"{r['tier']} {r['type']} {r['symbol']} {r['score']}/6 {r['pat']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f}(1%) T2:{r['t2']:.1f}(2%) 50% Trail\n"
else:
    if buys or sells:
        msg+=f"\nTop BUY: {buys[0]['symbol'] if buys else 'None'} | Top SELL: {sells[0]['symbol'] if sells else 'None'} - But 2 Active Full\n"
    else:
        msg+=f"\nNo Setup Now - NSE API Slow - Next 5Min Retry\n"

msg+=f"\nActive:\n"
for t in state['active']: msg+=f"{t['type']} {t['symbol']} E:{t['entry']:.1f} SL:{t['sl']:.1f}\n"

print(msg); send_tg(msg)
