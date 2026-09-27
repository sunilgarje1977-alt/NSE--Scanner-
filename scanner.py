import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime, timedelta
from SmartApi import SmartConnect

def clean(k):
    return os.getenv(k,"").strip().strip('"').strip("'")

API_KEY=clean('ANGEL_API_KEY')
CLIENT_ID=clean('ANGEL_CLIENT_ID')
PWD=clean('ANGEL_PASSWORD')
TOTP_SECRET=clean('ANGEL_TOTP_SECRET')
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN')
TELE_CHAT=clean('TELEGRAM_CHAT_ID')

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

def send_tg(msg):
    try:
        requests.get(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", params={"chat_id":TELE_CHAT,"text":msg}, timeout=10)
    except:
        pass

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")

with open("scrip_master.json") as f:
    master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

def get_pat(df):
    if len(df)<3:
        return []
    c1=df.iloc[-3];c2=df.iloc[-2];c=df.iloc[-1]
    pats=[]
    body=abs(c['Close']-c['Open'])+0.1
    low=min(c['Open'],c['Close'])-c['Low']
    up=c['High']-max(c['Open'],c['Close'])
    if low>body*2: pats.append("HAMMER")
    if up>body*2: pats.append("INV_HAMMER")
    if c2['Close']<c2['Open'] and c['Close']>c['Open'] and c['Close']>c2['Open']: pats.append("BULL_ENGULF")
    if c2['Close']>c2['Open'] and c['Close']<c['Open'] and c['Close']<c2['Open']: pats.append("BEAR_ENGULF")
    if c1['Close']<c1['Open'] and c['Close']>c['Open']: pats.append("MORNING_STAR")
    if c1['Close']>c1['Open'] and c['Close']<c['Open']: pats.append("EVENING_STAR")
    return pats

def get_movers():
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        s=requests.Session()
        s.get("https://www.nseindia.com",headers=headers,timeout=5)
        g=s.get("https://www.nseindia.com/api/live-analysis-variations?index=gainers",headers=headers,timeout=5).json()
        l=s.get("https://www.nseindia.com/api/live-analysis-variations?index=losers",headers=headers,timeout=5).json()
        gain=[x['symbol'] for x in g['NIFTY']['data'][:30]]
        lose=[x['symbol'] for x in l['NIFTY']['data'][:30]]
        return gain+lose
    except:
        return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","HAL","BEL","RVNL","PFC","TATASTEEL","ITC","LT","SBIN","TATAPOWER","POWERGRID"]

def analyze(sym):
    try:
        token=token_map.get(sym)
        if not token:
            return None
        fdate=(datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d %H:%M")
        tdate=datetime.now().strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":fdate,"todate":tdate})['data']
        df=pd.DataFrame(data,columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<40:
            return None
        ltp=df['Close'].iloc[-1]
        if ltp<20:
            return None
        if df['Volume'].iloc[-1]<10000:
            return None
        df['EMA9']=df['Close'].ewm(9).mean()
        df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3
        df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff()
        gain=delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2
        tr=pd.concat([df['High']-df['Low'],(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean()
        up=hl2+3*atr
        st=-1 if df['Close'].iloc[-1]>up.iloc[-2] else 1
        c=df.iloc[-1]
        c3h=df['High'].iloc[-4:-1].max()
        c3l=df['Low'].iloc[-4:-1].min()
        vavg=df['Volume'].iloc[-11:-1].mean()
        pats=get_pat(df)
        buy_pat=any(p in pats for p in ["HAMMER","BULL_ENGULF","MORNING_STAR"])
        sell_pat=any(p in pats for p in ["BEAR_ENGULF","EVENING_STAR"])
        buy_score=sum([c['Close']>c3h,c['EMA9']>c['VWAP'],c['EMA15']>c['VWAP'],st<0,c['RSI']>55,df['MACD'].iloc[-1]>0,c['Volume']>vavg])
        sell_score=sum([c['Close']<c3l,c['EMA9']<c['VWAP'],c['EMA15']<c['VWAP'],st>0,c['RSI']<45,df['MACD'].iloc[-1]<0,c['Volume']>vavg])
        if buy_pat and buy_score>=5:
            sl=min(c3l,ltp*0.98)
            if abs(ltp-sl)<ltp*0.005:
                return None
            r=ltp-sl
            return {"t":"BUY","s":sym,"sc":buy_score+1,"p":"+ ".join(pats),"ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*5,"tier":"STAR"}
        if buy_score>=6:
            sl=min(c3l,ltp*0.98)
            if abs(ltp-sl)<ltp*0.005:
                return None
            r=ltp-sl
            return {"t":"BUY","s":sym,"sc":buy_score,"p":"7/7 SETUP","ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*5,"tier":"GOOD"}
        if sell_pat and sell_score>=5:
            sl=max(c3h,ltp*1.02)
            if abs(sl-ltp)<ltp*0.005:
                return None
            r=sl-ltp
            return {"t":"SELL","s":sym,"sc":sell_score+1,"p":"+ ".join(pats),"ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*5,"tier":"STAR"}
        if sell_score>=6:
            sl=max(c3h,ltp*1.02)
            if abs(sl-ltp)<ltp*0.005:
                return None
            r=sl-ltp
            return {"t":"SELL","s":sym,"sc":sell_score,"p":"7/7 SETUP","ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*5,"tier":"GOOD"}
    except:
        return None
    return None

movers=get_movers()
buys=[]
sells=[]
for sym in movers[:50]:
    res=analyze(sym)
    if res:
        if res['t']=='BUY' and len(buys)<8:
            buys.append(res)
        if res['t']=='SELL' and len(sells)<8:
            sells.append(res)

msg=f"FAST NSE 750 + PATTERNS | {datetime.now().strftime('%H:%M')}\n"
msg+="\nBUY:\n"
if buys:
    for r in buys:
        msg+=f"{r['tier']} BUY {r['s']} {r['sc']}/8 {r['p']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} T2:{r['t2']:.1f}\n"
else:
    msg+="No BUY Today\n"
msg+="\nSELL:\n"
if sells:
    for r in sells:
        msg+=f"{r['tier']} SELL {r['s']} {r['sc']}/8 {r['p']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} T2:{r['t2']:.1f}\n"
else:
    msg+="No SELL Today\n"

print(msg)
send_tg(msg)
