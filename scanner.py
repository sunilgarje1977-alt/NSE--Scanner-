import os, json, pyotp, requests, urllib.request, concurrent.futures
import pandas as pd
from datetime import datetime, timedelta
from SmartApi import SmartConnect

def clean(k):
    return os.getenv(k,"").strip().strip('"').strip("'")

TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN')
TELE_CHAT=clean('TELEGRAM_CHAT_ID')
API_KEY=clean('ANGEL_API_KEY')
CLIENT_ID=clean('ANGEL_CLIENT_ID')
PWD=clean('ANGEL_PASSWORD')
TOTP_SECRET=clean('ANGEL_TOTP_SECRET')

def send_tg(msg):
    if not TELE_TOKEN or not TELE_CHAT:
        print(msg)
        return
    url=f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
    for i in range(0,len(msg),3800):
        try:
            requests.post(url, json={"chat_id":TELE_CHAT,"text":msg[i:i+3800],"parse_mode":"Markdown"}, timeout=15)
        except:
            pass

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f:
    master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

REAL_1000CR=["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","AXISBANK","BAJFINANCE","MARUTI","WIPRO","HCLTECH","ULTRACEMCO","ASIANPAINT","TITAN","ONGC","HAL","BEL","BDL","GRSE","MAZDOCK","RVNL","NHPC","SJVN","IRCTC","COCHINSHIP","BHEL","PFC","RECLTD","IRFC","TATAPOWER","NTPC","POWERGRID","COALINDIA","JSWSTEEL","TATASTEEL","HINDALCO","VEDL","SAIL","JINDALSTEL","NMDC","ADANIENT","ADANIPORTS","ADANIGREEN","ADANIPOWER","JSWENERGY","GAIL","OIL","PETRONET","IGL","MGL","BPCL","IOC","M&M","TATAMOTORS","EICHERMOT","BAJAJ-AUTO","HEROMOTOCO","TVSMOTOR","ASHOKLEY","MRF","BALKRISIND","APOLLOTYRE","BHARATFORG","MOTHERSON","SUNPHARMA","DIVISLAB","DRREDDY","CIPLA","LUPIN","AUROPHARMA","ZYDUSLIFE","ALKEM","TORNTPHARM","IPCALAB","SYNGENE","LAURUSLABS","GLENMARK","BIOCON","SBILIFE","HDFCLIFE","ICICIPRULI","ICICIGI","LICI","BAJAJFINSV","MUTHOOTFIN","CHOLAFIN","SHRIRAMFIN","LICHSGFIN","POONAWALLA","SBICARD","M&MFIN","CREDITACC","DMART","TRENT","PIDILITEX","HAVELLS","VOLTAS","DIXON","KAYNES","AMBER","SYRMA","TATAELXSI","PERSISTENT","COFORGE","MPHASIS","LTIM","LTTS","KPITTECH","TATATECH","TECHM","BSE","MCX","CAMS","CDSL","KFINTECH","IEX","ANGELONE","NUVAMA","MOTILALOFS","HDFCAMC","POLYCAB","KEI","ASTRAL","SUPREMEIND","APLAPOLLO","BOSCHLTD","ABB","SIEMENS","CUMMINSIND","THERMAX","SKFINDIA","TIMKEN","HONAUT","3MINDIA","AIAENG","GRASIM","SHREECEM","ACC","AMBUJACEM","DALBHARAT","JKCEMENT","RAMCOCEM","BANKBARODA","CANBK","PNB","UNIONBANK","INDUSINDBK","FEDERALBNK","IDFCFIRSTB","AUBANK","BANDHANBNK","RBLBANK","IDBI","BANKINDIA","MAHABANK","PAYTM","ZOMATO","NYKAA","DELHIVERY","POLICYBZR","INDIAMART","AFFLE","TANLA","MAPMYINDIA","NAUKRI","ISGEC"]

SYMBOLS=list(dict.fromkeys([s for s in REAL_1000CR if s in token_map]))

def get_gain(sym):
    try:
        token=token_map.get(sym)
        d=smart.ltpData("NSE", sym+"-EQ", token)['data']
        ltp=float(d['ltp']); open_p=float(d.get('open',ltp))
        pct=(ltp-open_p)/open_p*100 if open_p else 0
        return {"symbol":sym,"pct":pct,"token":token}
    except:
        return None

filtered=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    for r in ex.map(get_gain, SYMBOLS):
        if r:
            filtered.append(r)

top10_gainers=sorted(filtered,key=lambda x:x['pct'],reverse=True)[:10]
top10_losers=sorted(filtered,key=lambda x:x['pct'])[:10]

def supertrend_dir(df):
    hl2=(df['High']+df['Low'])/2
    tr=pd.concat([(df['High']-df['Low']),(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(10).mean()
    lower=hl2-3*atr; upper=hl2+3*atr
    direction=pd.Series(1,index=df.index)
    for i in range(1,len(df)):
        if df['Close'].iloc[i]<=lower.iloc[i-1]:
            direction.iloc[i]=1
        elif df['Close'].iloc[i]>=upper.iloc[i-1]:
            direction.iloc[i]=-1
        else:
            direction.iloc[i]=direction.iloc[i-1]
    return direction

def check_signal(stock_obj):
    sym=stock_obj['symbol']; token=stock_obj['token']
    try:
        to_date=datetime.now(); from_date=to_date-timedelta(days=10)
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")})['data']
        df=pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<20:
            return None
        df['EMA9']=df['Close'].ewm(span=9).mean()
        df['EMA15']=df['Close'].ewm(span=15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3
        df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff()
        gain=delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        df['MACD']=df['Close'].ewm(span=12).mean()-df['Close'].ewm(span=26).mean()
        df['DIR']=supertrend_dir(df)
        c1=df.iloc[-4]; c4=df.iloc[-1]
        avg_vol=df['Volume'].iloc[-10:-1].mean()
        buy_score=sum([c4['Close']>c1['High'], c4['EMA9']>c4['VWAP'], c4['EMA15']>c4['VWAP'], df['DIR'].iloc[-1]<0, c4['RSI']>50, df['MACD'].iloc[-1]>0, c4['Volume']>avg_vol*1.1])
        sell_score=sum([c4['Close']<c1['Low'], c4['EMA9']<c4['VWAP'], c4['EMA15']<c4['VWAP'], df['DIR'].iloc[-1]>0, c4['RSI']<50, df['MACD'].iloc[-1]<0, c4['Volume']>avg_vol*1.1])
        if buy_score>=5:
            return ("BUY",f"🟢 BUY DONE: {sym} @ {c4['Close']:.0f} ({stock_obj['pct']:+.2f}%) Score {buy_score}/7")
        if sell_score>=5:
            return ("SELL",f"🔴 SELL DONE: {sym} @ {c4['Close']:.0f} ({stock_obj['pct']:+.2f}%) Score {sell_score}/7")
    except:
        pass
    return None

gainer_results=[]; loser_results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    for f in concurrent.futures.as_completed([ex.submit(check_signal,s) for s in top10_gainers]):
        if f.result():
            gainer_results.append(f.result())
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    for f in concurrent.futures.as_completed([ex.submit(check_signal,s) for s in top10_losers]):
        if f.result():
            loser_results.append(f.result())

all_res=gainer_results+loser_results
buy_done=[r[1] for r in all_res if r[0]=="BUY"]
sell_done=[r[1] for r in all_res if r[0]=="SELL"]
now=datetime.now().strftime("%d-%m-%Y %H:%M")
msg=f"⚡️ *1000Cr+ SCAN V8 - FINAL STRONG*\nTime: {now}\n\n"
msg+=f"*TOP 10 GAINERS (1000Cr+):*\n" + "\n".join([f"{x['symbol']} {x['pct']:+.2f}%" for x in top10_gainers])
msg+=f"\n\n*TOP 10 LOSERS (1000Cr+):*\n" + "\n".join([f"{x['symbol']} {x['pct']:+.2f}%" for x in top10_losers])
msg+=f"\n\n✅ *TOTAL BUY DONE ({len(buy_done)}):*\n" + ("\n".join(buy_done) if buy_done else "No Buy Today - Market Closed (Sunday)")
msg+=f"\n\n❌ *TOTAL SELL DONE ({len(sell_done)}):*\n" + ("\n".join(sell_done) if sell_done else "No Sell Today - Market Closed (Sunday)")
msg+=f"\n\n_Note: Sunday ला Data नाही म्हणून 0 आहे. Monday 9:30 ला पक्के Signal येतील._"
print(msg)
send_tg(msg)
