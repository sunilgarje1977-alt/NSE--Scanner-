"""
FINAL V3 - 1000Cr+ | Angel API | Top 10 G/L | BUY DONE / SELL DONE
Speed: 10-15 Sec
"""
import pandas as pd, requests, os, concurrent.futures, pyotp, json, urllib.request
from datetime import datetime, timedelta
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN')
TELE_CHAT=clean('TELEGRAM_CHAT_ID')
API_KEY=clean('ANGEL_API_KEY')
CLIENT_ID=clean('ANGEL_CLIENT_ID')
PWD=clean('ANGEL_PASSWORD')
TOTP_SECRET=clean('ANGEL_TOTP_SECRET')

def send_tg(msg):
    if not TELE_TOKEN or not TELE_CHAT: print(msg); return
    url=f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
    for i in range(0,len(msg),3800):
        try: requests.post(url, json={"chat_id":TELE_CHAT,"text":msg[i:i+3800],"parse_mode":"Markdown"},timeout=15)
        except: pass

# Angel Login
smart = SmartConnect(api_key=API_KEY)
totp = pyotp.TOTP(TOTP_SECRET).now()
smart.generateSession(CLIENT_ID, PWD, totp)
print("Angel Login Done")

# Scrip Master
if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f:
    master=json.load(f)
token_map={}
for s in master:
    if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ'):
        token_map[s['name']]=s['token']

# === 1000Cr+ TRUE LIST (700 Stocks) - No Penny ===
REAL_1000CR = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","AXISBANK","BAJFINANCE","MARUTI","WIPRO","HCLTECH","ULTRACEMCO","ASIANPAINT","TITAN","ONGC","HAL","BEL","BDL","GRSE","MAZDOCK","RVNL","NHPC","SJVN","IRCTC","COCHINSHIP","BHEL","PFC","RECLTD","IRFC","TATAPOWER","NTPC","POWERGRID","COALINDIA","JSWSTEEL","TATASTEEL","HINDALCO","VEDL","SAIL","JINDALSTEL","NMDC","ADANIENT","ADANIPORTS","ADANIGREEN","ADANIPOWER","JSWENERGY","GAIL","OIL","PETRONET","IGL","MGL","BPCL","IOC","M&M","TATAMOTORS","EICHERMOT","BAJAJ-AUTO","HEROMOTOCO","TVSMOTOR","ASHOKLEY","MRF","BALKRISIND","APOLLOTYRE","BHARATFORG","MOTHERSON","SUNPHARMA","DIVISLAB","DRREDDY","CIPLA","LUPIN","AUROPHARMA","ZYDUSLIFE","ALKEM","TORNTPHARM","IPCALAB","SYNGENE","LAURUSLABS","GLENMARK","BIOCON","AJANTPHARM","NATCOPHARM","GRANULES","JBCHEPHARM","ALEMBICLTD","PFIZER","SANOFI","ABBOTINDIA","SBILIFE","HDFCLIFE","ICICIPRULI","ICICIGI","LICI","BAJAJFINSV","MUTHOOTFIN","CHOLAFIN","SHRIRAMFIN","LICHSGFIN","POONAWALLA","SBICARD","M&MFIN","CREDITACC","MANAPPURAM","DMART","TRENT","PIDILITEX","HAVELLS","VOLTAS","DIXON","KAYNES","AMBER","SYRMA","TATAELXSI","PERSISTENT","COFORGE","MPHASIS","LTIM","LTTS","KPITTECH","TATATECH","TECHM","BSE","MCX","CAMS","CDSL","KFINTECH","IEX","ANGELONE","NUVAMA","MOTILALOFS","HDFCAMC","POLYCAB","KEI","ASTRAL","SUPREMEIND","APLAPOLLO","BOSCHLTD","ABB","SIEMENS","CUMMINSIND","THERMAX","SKFINDIA","TIMKEN","HONAUT","3MINDIA","AIAENG","LT","GRASIM","SHREECEM","ACC","AMBUJACEM","DALBHARAT","JKCEMENT","RAMCOCEM","BANKBARODA","CANBK","PNB","UNIONBANK","INDUSINDBK","FEDERALBNK","IDFCFIRSTB","AUBANK","BANDHANBNK","RBLBANK","IDBI","BANKINDIA","MAHABANK","INDIANB","CUB","KARURVYSYA","CITYUNION","PAYTM","ZOMATO","NYKAA","DELHIVERY","POLICYBZR","INDIAMART","AFFLE","TANLA","MAPMYINDIA","NAUKRI","ZENSAR","MPHASIS","SONATSOFTW","CYIENT","LTTS","HINDPETRO","MRPL","CHENNPETRO","AEGISLOG","DEEPAKNTR","NAVINFLUOR","SRF","ATUL","VINATIORG","BALRAMCHIN","EIDPARRY","CHAMBLFERT","GNFC","GSFC","RCF","FACT","TATACHEM","UPL","PIIND","SUMICHEM","BAYERCROP","DHANUKA","ASTRAZEN","JBCHEPHARM","JUBLINGREA","JUBLFOOD","DEVYANI","SAPPHIRE","WESTLIFE","KALYANKJIL","SENC0","BATAINDIA","RELAXO","CAMPUS","METROBRAND","TRENT","PAGEIND","KPRMILL","RAYMOND","TRIDENT","VARDMNPOLY","WELSPUNLIV","ALOKINDS","CUPID","CROMPTON","ORIENTELEC","VGUARD","HAVELLS","POLYCAB","FINCABLES","KEI","BATA","VOLTAS","WHIRLPOOL","BLUESTARCO","AMBER","DIXON","KAYNES","CGPOWER","BHEL","SIEMENS","ABB","SCHNEIDER","HONAUT","THERMAX","PRAJIND","ISGEC","LAXMIMACH","TIMKEN","SKFINDIA","GRINDWELL","CARBORUNDU","AIAENG","MMFORG","BHARATFORG","MOTHERSON","SONACOMS","ENDURANCE","MINDACORP","SUPRAJIT","JAMNAAUTO","GABRIEL","MUNJALSHOWA","JTEKTINDIA","SANDHAR","SUBROS","FIEM","LUMAXTECH","LUMAXIND","JKTYRE","CEATLTD","APOLLOTYRE","BALKRISIND","MRF","TVSSCS","TIINDIA","ASHOKLEY","EICHERMOT","BAJAJ-AUTO","HEROMOTOCO","TVSMOTOR","MARUTI","M&M","TATAMOTORS","FORCE","OLECTRA","JBM","TATAPOWER","NTPC","POWERGRID","JSWENERGY","ADANIGREEN","ADANIPOWER","TORNTPOWER","CESC","TATAPOWER","NHPC","SJVN","THOMASCOOK","IRCTC","INDIGO","SPICEJET","INTERGLOBE","TITAN","TATAELXSI","KPITTECH"]

SYMBOLS = [s for s in REAL_1000CR if s in token_map]

def get_gain(sym):
    try:
        token=token_map.get(sym)
        ltp_data = smart.ltpData("NSE", sym+"-EQ", token)
        ltp = float(ltp_data['data']['ltp'])
        open_p = float(ltp_data['data'].get('open', ltp))
        pct = (ltp-open_p)/open_p*100 if open_p else 0
        return {"symbol":sym, "pct":pct, "price":ltp, "token":token}
    except: return None

filtered=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    for r in ex.map(get_gain, SYMBOLS):
        if r: filtered.append(r)

top10_gainers=sorted(filtered,key=lambda x:x['pct'],reverse=True)[:10]
top10_losers=sorted(filtered,key=lambda x:x['pct'])[:10]
FINAL_20=top10_gainers+top10_losers

def supertrend_dir(df, period=10, mult=3):
    hl2=(df['High']+df['Low'])/2
    tr1=df['High']-df['Low']
    tr2=(df['High']-df['Close'].shift()).abs()
    tr3=(df['Low']-df['Close'].shift()).abs()
    tr=pd.concat([tr1,tr2,tr3],axis=1).max(axis=1)
    atr=tr.rolling(period).mean()
    upper=hl2+mult*atr; lower=hl2-mult*atr
    dir=pd.Series(1,index=df.index)
    for i in range(1,len(df)):
        if df['Close'].iloc[i]<=lower.iloc[i-1]: dir.iloc[i]=1
        elif df['Close'].iloc[i]>=upper.iloc[i-1]: dir.iloc[i]=-1
        else: dir.iloc[i]=dir.iloc[i-1]
    return dir

def check(stock_obj):
    sym=stock_obj['symbol']; token=stock_obj['token']
    try:
        to_date=datetime.now(); from_date=to_date - timedelta(days=10)
        historic = smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")})
        df=pd.DataFrame(historic['data'], columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<50: return None
        df['EMA9']=df['Close'].ewm(9).mean()
        df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3
        df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff()
        gain=delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        df['MACD']=df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
        df['SIGNAL']=df['MACD'].ewm(span=9).mean()
        df['HIST']=df['MACD']-df['SIGNAL']
        df['DIR']=supertrend_dir(df,10,3)
        last=df.iloc[-1]; p1=df.iloc[-2]
        unusualVol = last['Volume'] > p1['Volume']

        buyPattern = (df['Close'].iloc[-3] > df['Open'].iloc[-3]) and (p1['Close'] < p1['Open']) and (last['Close'] > df['High'].iloc[-3])
        sellPattern = (df['Close'].iloc[-3] < df['Open'].iloc[-3]) and (p1['Close'] > p1['Open']) and (last['Close'] < df['Low'].iloc[-3])

        score_buy = int(last['EMA9']>last['VWAP']) + int(last['EMA15']>last['VWAP']) + int(last['DIR']<0) + int(last['RSI']>55) + int(last['MACD']>0) + int(unusualVol)
        score_sell = int(last['EMA9']<last['VWAP']) + int(last['EMA15']<last['VWAP']) + int(last['DIR']>0) + int(last['RSI']<45) + int(last['MACD']<0) + int(unusualVol)

        if buyPattern and score_buy>=6:
            return ("BUY", f"🟢 BUY DONE: {sym} @ {last['Close']:.2f} ({stock_obj['pct']:+.2f}%) Score {score_buy}/6")
        if sellPattern and score_sell>=6:
            return ("SELL", f"🔴 SELL DONE: {sym} @ {last['Close']:.2f} ({stock_obj['pct']:+.2f}%) Score {score_sell}/6")
    except Exception as e: print(sym,e)
    return None

buy_done=[]; sell_done=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for r in ex.map(check, FINAL_20):
        if r:
            if r[0]=="BUY": buy_done.append(r[1])
            else: sell_done.append(r[1])

now=datetime.now().strftime("%d-%m %H:%M")
msg=f"⚡️ *ANGEL FAST SCAN - 1000Cr+ | Top 10 G/L (20 Stocks)*\nTime: {now}\n\n"
msg+=f"*TOP 10 GAINERS (1000Cr+):*\n" + "\n".join([f"{x['symbol']} {x['pct']:+.2f}%" for x in top10_gainers])
msg+=f"\n\n*TOP 10 LOSERS (1000Cr+):*\n" + "\n".join([f"{x['symbol']} {x['pct']:+.2f}%" for x in top10_losers])
msg+=f"\n\n✅ *BUY DONE ({len(buy_done)}):*\n" + ("\n".join(buy_done) if buy_done else "No Buy Today - Wait for Breakout")
msg+=f"\n\n❌ *SELL DONE ({len(sell_done)}):*\n" + ("\n".join(sell_done) if sell_done else "No Sell Today")

print(msg)
send_tg(msg)
