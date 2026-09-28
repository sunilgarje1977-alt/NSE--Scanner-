import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime, timedelta
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
API_KEY=clean('ANGEL_API_KEY'); CLIENT_ID=clean('ANGEL_CLIENT_ID'); PWD=clean('ANGEL_PASSWORD'); TOTP_SECRET=clean('ANGEL_TOTP_SECRET')
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN'); TELE_CHAT=clean('TELEGRAM_CHAT_ID')

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

def send_tg(msg):
    try: requests.get(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", params={"chat_id":TELE_CHAT,"text":msg}, timeout=10)
    except: pass

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f: master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

def get_movers_750():
    all_sym=[]
    try:
        headers={"User-Agent":"Mozilla/5.0"}
        s=requests.Session(); s.get("https://www.nseindia.com",headers=headers,timeout=10)
        g=s.get("https://www.nseindia.com/api/live-analysis-variations?index=gainers",headers=headers,timeout=10).json()
        l=s.get("https://www.nseindia.com/api/live-analysis-variations?index=losers",headers=headers,timeout=10).json()
        for key in g:
            if isinstance(g[key], dict) and 'data' in g[key]:
                all_sym += [x['symbol'] for x in g[key]['data'][:20]]
        for key in l:
            if isinstance(l[key], dict) and 'data' in l[key]:
                all_sym += [x['symbol'] for x in l[key]['data'][:20]]
        all_sym=list(dict.fromkeys(all_sym))
        return all_sym[:60]
    except:
        return ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","HAL","BEL","BDL","MAZDOCK","RVNL","IRFC","PFC","RECLTD","NHPC","BHEL","SAIL","TATASTEEL","JSWSTEEL","TATAMOTORS","M&M","POWERGRID","TATAPOWER","ADANIENT","ADANIGREEN","SUZLON","IRCTC","ZOMATO","POLYCAB","DIXON","KPITTECH"]

def get_pat(df):
    if len(df)<5: return []
    c1=df.iloc[-3]; c2=df.iloc[-2]; c=df.iloc[-1]
    pats=[]; body=abs(c['Close']-c['Open'])+0.1
    low=min(c['Open'],c['Close'])-c['Low']; up=c['High']-max(c['Open'],c['Close'])
    if low>body*2: pats.append("HAMMER")
    if up>body*2: pats.append("INV_HAMMER")
    if c2['Close']<c2['Open'] and c['Close']>c['Open'] and c['Close']>c2['Open']: pats.append("BULL_ENGULF")
    if c2['Close']>c2['Open'] and c['Close']<c['Open'] and c['Close']<c2['Open']: pats.append("BEAR_ENGULF")
    if c1['Close']<c1['Open'] and c2['Close']<c2['Open']*0.99 and c['Close']>c['Open']: pats.append("MORNING_STAR")
    if c1['Close']>c1['Open'] and c2['Close']>c2['Open']*1.01 and c['Close']<c['Open']: pats.append("EVENING_STAR")
    # 3 White / 3 Black Soldiers
    if df['Close'].iloc[-3:].is_monotonic_increasing and (df['Close'].iloc[-3:]>df['Open'].iloc[-3:]).all(): pats.append("3WHITE")
    if df['Close'].iloc[-3:].is_monotonic_decreasing and (df['Close'].iloc[-3:]<df['Open'].iloc[-3:]).all(): pats.append("3BLACK")
    return pats

def analyze(sym):
    try:
        token=token_map.get(sym)
        if not token: return None
        fdate=(datetime.now()-timedelta(days=10)).strftime("%Y-%m-%d %H:%M"); tdate=datetime.now().strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":fdate,"todate":tdate})['data']
        df=pd.DataFrame(data,columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<40: return None
        ltp=df['Close'].iloc[-1]
        if ltp<25: return None
        # 7 CONDITIONS CALCULATION
        df['EMA9']=df['Close'].ewm(9).mean()
        df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3
        df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2
        tr=pd.concat([df['High']-df['Low'],(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); up=hl2+3*atr; st=-1 if df['Close'].iloc[-1]>up.iloc[-2] else 1
        c=df.iloc[-1]; c3h=df['High'].iloc[-4:-1].max(); c3l=df['Low'].iloc[-4:-1].min(); vavg=df['Volume'].iloc[-11:-1].mean()
        pats=get_pat(df)
        buy_pat=any(p in pats for p in ["HAMMER","BULL_ENGULF","MORNING_STAR","3WHITE"])
        sell_pat=any(p in pats for p in ["INV_HAMMER","BEAR_ENGULF","EVENING_STAR","3BLACK"])
        # 7/7 SCORE
        buy_score=sum([c['Close']>c3h, c['EMA9']>c['VWAP'], c['EMA15']>c['VWAP'], st<0, c['RSI']>55, df['MACD'].iloc[-1]>0, c['Volume']>vavg])
        sell_score=sum([c['Close']<c3l, c['EMA9']<c['VWAP'], c['EMA15']<c['VWAP'], st>0, c['RSI']<45, df['MACD'].iloc[-1]<0, c['Volume']>vavg])
        # 7/7 LOGIC
        if buy_pat and buy_score>=5:
            sl=min(c3l,ltp*0.98); r=ltp-sl
            if r<ltp*0.003: return None
            return {"t":"BUY","s":sym,"sc":f"{buy_score+1}/8","p":"+ ".join(pats),"ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*5,"tier":"STAR ⭐"}
        if buy_score>=6:
            sl=min(c3l,ltp*0.98); r=ltp-sl
            if r<ltp*0.003: return None
            return {"t":"BUY","s":sym,"sc":f"{buy_score}/7","p":"7/7 SETUP","ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*5,"tier":"GOOD"}
        if sell_pat and sell_score>=5:
            sl=max(c3h,ltp*1.02); r=sl-ltp
            if r<ltp*0.003: return None
            return {"t":"SELL","s":sym,"sc":f"{sell_score+1}/8","p":"+ ".join(pats),"ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*5,"tier":"STAR ⭐"}
        if sell_score>=6:
            sl=max(c3h,ltp*1.02); r=sl-ltp
            if r<ltp*0.003: return None
            return {"t":"SELL","s":sym,"sc":f"{sell_score}/7","p":"7/7 SETUP","ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*5,"tier":"GOOD"}
    except: return None
    return None

movers=get_movers_750(); buys=[]; sells=[]
for sym in movers[:60]:
    res=analyze(sym)
    if res:
        if res['t']=='BUY' and len(buys)<8: buys.append(res)
        if res['t']=='SELL' and len(sells)<8: sells.append(res)

msg=f"🔥 NSE 750 7/7 + PATTERN | {datetime.now().strftime('%H:%M')}\nFilter: Large+Mid+Small Gainers/Losers\n\nBUY:\n"
if buys:
    for r in buys: msg+=f"{r['tier']} {r['t']} {r['s']} {r['sc']} {r['p']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} T2:{r['t2']:.1f}\n"
else: msg+="No BUY 7/7 Today (Sunday)\n"
msg+="\nSELL:\n"
if sells:
    for r in sells: msg+=f"{r['tier']} {r['t']} {r['s']} {r['sc']} {r['p']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} T2:{r['t2']:.1f}\n"
else: msg+="No SELL 7/7 Today (Sunday)\n"
print(msg); send_tg(msg)
