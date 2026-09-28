import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime, timedelta, timezone
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
API_KEY=clean('ANGEL_API_KEY'); CLIENT_ID=clean('ANGEL_CLIENT_ID'); PWD=clean('ANGEL_PASSWORD'); TOTP_SECRET=clean('ANGEL_TOTP_SECRET')
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN'); TELE_CHAT=clean('TELEGRAM_CHAT_ID')

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

# === BALANCED NSE 750 - LARGE 20 + MID 20 + SMALL 20 ===
def get_nse_750_movers():
    headers={"User-Agent":"Mozilla/5.0"}
    s=requests.Session()
    try: s.get("https://www.nseindia.com",headers=headers,timeout=5)
    except: pass
    
    final_list=[]
    indices = [("NIFTY 100","LARGE"), ("NIFTY MIDCAP 150","MID"), ("NIFTY SMALLCAP 250","SMALL")]
    
    for idx_name, cat in indices:
        try:
            url=f"https://www.nseindia.com/api/equity-stockIndices?index={idx_name.replace(' ','%20')}"
            r=s.get(url,headers=headers,timeout=10).json()
            if 'data' in r:
                data = [x for x in r['data'] if x.get('lastPrice',0)>50]
                df = pd.DataFrame(data).sort_values('pChange', ascending=False)
                top10 = df.head(10)['symbol'].tolist() # Top 10 Gainers of this cap
                bottom10 = df.tail(10)['symbol'].tolist() # Top 10 Losers of this cap
                final_list.extend(top10 + bottom10)
                print(f"{cat} {idx_name}: Gainers {top10[:2]} Losers {bottom10[:2]}")
        except Exception as e:
            print(f"{cat} Fail {e}")

    if len(final_list)<30:
        print("API Fail -> Hardcoded Balanced Mix")
        final_list = [
            # LARGE 20
            "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","MARUTI","TITAN","SUNPHARMA","NTPC","POWERGRID","ONGC","TATAMOTORS","JSWSTEEL","TATASTEEL","BAJFINANCE","ULTRACEMCO",
            # MID 20
            "HAL","BEL","BDL","MAZDOCK","RVNL","IRFC","PFC","RECLTD","BHEL","SAIL","NHPC","SJVN","NMDC","BANKBARODA","PNB","CANBK","IDFCFIRSTB","ASHOKLEY","MOTHERSON","TATAPOWER",
            # SMALL 20
            "POLYCAB","DIXON","KPITTECH","PERSISTENT","BSE","CDSL","KAYNES","TATAELXSI","IEX","MCX","SUZLON","ZOMATO","IRCTC","IDEA","YESBANK","HFCL","NBCC","JPASSOCIAT","RENUKA","RPOWER"
        ]
    return final_list[:60]

def get_pat(df):
    if len(df)<4: return []
    c2=df.iloc[-2]; c=df.iloc[-1]
    pats=[]; body=abs(c['Close']-c['Open'])+0.1
    low=min(c['Open'],c['Close'])-c['Low']; up=c['High']-max(c['Open'],c['Close'])
    if low>body*1.8: pats.append("HAMMER")
    if up>body*1.8: pats.append("INV_HAMMER")
    if c2['Close']<c2['Open'] and c['Close']>c['Open'] and c['Close']>c2['Open']: pats.append("BULL_ENGULF")
    if c2['Close']>c2['Open'] and c['Close']<c['Open'] and c['Close']<c2['Open']: pats.append("BEAR_ENGULF")
    return pats

def analyze(sym):
    try:
        token=token_map.get(sym)
        if not token: return None
        fdate=(ist_now-timedelta(days=5)).strftime("%Y-%m-%d %H:%M"); tdate=ist_now.strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":fdate,"todate":tdate})['data']
        df=pd.DataFrame(data,columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<35: return None
        ltp=df['Close'].iloc[-1]
        if ltp<50: return None
        df['EMA9']=df['Close'].ewm(9).mean(); df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3; df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss)); df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2; tr=pd.concat([df['High']-df['Low'],(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); up=hl2+3*atr; st=-1 if df['Close'].iloc[-1]>up.iloc[-2] else 1
        c=df.iloc[-1]; c3h=df['High'].iloc[-4:-1].max(); c3l=df['Low'].iloc[-4:-1].min(); vavg=df['Volume'].iloc[-11:-1].mean()
        pats=get_pat(df)
        buy_pat=any(p in pats for p in ["HAMMER","BULL_ENGULF"]); sell_pat=any(p in pats for p in ["INV_HAMMER","BEAR_ENGULF"])
        buy_score=sum([c['Close']>c3h, c['EMA9']>c['VWAP'], c['EMA15']>c['VWAP'], st<0, c['RSI']>55, df['MACD'].iloc[-1]>0, c['Volume']>vavg])
        sell_score=sum([c['Close']<c3l, c['EMA9']<c['VWAP'], c['EMA15']<c['VWAP'], st>0, c['RSI']<45, df['MACD'].iloc[-1]<0, c['Volume']>vavg])
        if buy_pat and buy_score>=5:
            sl=min(c3l,ltp*0.985); r=ltp-sl; 
            if r<ltp*0.004: return None
            return {"t":"BUY","s":sym,"sc":f"{buy_score+1}/8","p":"+ ".join(pats),"ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*4,"tier":"STAR ⭐"}
        if buy_score>=6:
            sl=min(c3l,ltp*0.985); r=ltp-sl;
            if r<ltp*0.004: return None
            return {"t":"BUY","s":sym,"sc":f"{buy_score}/7","p":"7/7 SETUP","ltp":ltp,"sl":sl,"t1":ltp+r*2,"t2":ltp+r*4,"tier":"GOOD"}
        if sell_pat and sell_score>=5:
            sl=max(c3h,ltp*1.015); r=sl-ltp;
            if r<ltp*0.004: return None
            return {"t":"SELL","s":sym,"sc":f"{sell_score+1}/8","p":"+ ".join(pats),"ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*4,"tier":"STAR ⭐"}
        if sell_score>=6:
            sl=max(c3h,ltp*1.015); r=sl-ltp;
            if r<ltp*0.004: return None
            return {"t":"SELL","s":sym,"sc":f"{sell_score}/7","p":"7/7 SETUP","ltp":ltp,"sl":sl,"t1":ltp-r*2,"t2":ltp-r*4,"tier":"GOOD"}
    except: return None

movers=get_nse_750_movers(); buys=[]; sells=[]
for sym in movers[:60]:
    res=analyze(sym)
    if res:
        if res['t']=='BUY' and len(buys)<15: buys.append(res)
        if res['t']=='SELL' and len(sells)<15: sells.append(res)

msg=f"🔥 LIVE 7/7 BALANCED | {ist_now.strftime('%d %b %H:%M')} IST\nLARGE(20)+MID(20)+SMALL(20) = 60 Scan\n\nBUY ({len(buys)}):\n"
if buys:
    for r in buys: msg+=f"{r['tier']} {r['s']} {r['sc']} {r['p']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} T2:{r['t2']:.1f}\n"
else: msg+="No BUY Now\n"
msg+=f"\nSELL ({len(sells)}):\n"
if sells:
    for r in sells: msg+=f"{r['tier']} {r['s']} {r['sc']} {r['p']} E:{r['ltp']:.1f} SL:{r['sl']:.1f} T1:{r['t1']:.1f} T2:{r['t2']:.1f}\n"
else: msg+="No SELL Now\n"
print(msg); send_tg(msg)
