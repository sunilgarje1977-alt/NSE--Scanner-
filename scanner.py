import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta

STATE_FILE = "active_trades.json"
PNL_FILE = "pnl_history.json"

def load_state():
    if not os.path.exists(STATE_FILE): return {"active":[],"pending":[]}
    try:
        with open(STATE_FILE,'r') as f: return json.load(f)
    except: return {"active":[],"pending":[]}

def save_state(active, pending):
    with open(STATE_FILE,'w') as f: json.dump({"active":active,"pending":pending}, f)

def load_pnl():
    if not os.path.exists(PNL_FILE): return []
    try:
        with open(PNL_FILE,'r') as f: return json.load(f)
    except: return []

def save_pnl(data):
    with open(PNL_FILE,'w') as f: json.dump(data,f)

def send_telegram(bot_token, chat_id, msg):
    try:
        if not bot_token or not chat_id:
            print("TELEGRAM SECRET MISSING")
            return
        r=requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data={"chat_id":chat_id,"text":msg}, timeout=15)
        print(f"Telegram Status: {r.status_code}")
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_token_map():
    try:
        url="https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data=requests.get(url,timeout=20).json()
        mp={i['symbol'].replace('-EQ',''):i['token'] for i in data if i.get('exch_seg')=='NSE' and i.get('symbol')}
        return mp
    except: return {}

TOKEN_MAP=get_token_map()

def get_1000_with_category():
    # FAST - NO NSE API - DIRECT 600 LIST
    LARGE = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","BEL","HAL","BSE","MCX","TATAPOWER","TATAMOTORS","WIPRO","TECHM","HCLTECH","GRASIM","CIPLA","DIVISLAB","DRREDDY","BRITANNIA","EICHERMOT","HEROMOTOCO","M&M","BAJAJ-AUTO","INDUSINDBK","SBILIFE","HDFCLIFE","ICICIPRULI","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","HAL","BEML","BHEL","CONCOR","NHPC","SJVN","NMDC","SAIL","HINDZINC","VEDL","JSWENERGY","TATAELXSI","LTIM","LICI","GAIL","PETRONET","ADANIGREEN","ADANIPOWER"]

    MID = ["BANKBARODA","PNB","CANBK","IDFCFIRSTB","BANDHANBNK","AUBANK","FEDERALBNK","CUB","RBLBANK","IDFC","PNBHOUSING","MUTHOOTFIN","CHOLAFIN","M&MFIN","SUNDARMFIN","POONAWALLA","CREDITACC","UJJIVAN","COFORGE","PERSISTENT","MPHASIS","KPITTECH","DIXON","KAYNES","POLYCAB","KEI","BSOFT","APOLLOHOSP","MAXHEALTH","FORTIS","AUROPHARMA","LUPIN","ALKEM","GODREJPROP","OBEROIRLTY","PRESTIGE","DLF","PIDILITIND","SRF","ATUL","AARTIIND","DEEPAKNTR","VINATIORG","TATACHEM","CHAMBLFERT","COROMANDEL","GNFC","NATIONALUM","JINDALSTEL","APLAPOLLO","WELCORP","TATACOMM","TATAPOWER"]

    SMALL = ["ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","CDSL","ANGELONE","AFFLE","AARTIIND","TEJASNET","HFCL","RAILTEL","IRCON","MAZAGON","GARDENREACH","COCHINSHIP","PRAJIND","JPOWER","TATACHEM","CHAMBLFERT","DEEPAKNTR","ATUL","TANLA","EASEMYTRIP","UCOBANK","IOB","MAHABANK","UNIONBANK","CENTRALBK","MOTILALOFS","CAMS","KFINTECH","RENUKA","BALRAMCHIN","TATAINVEST","VBL","JWL","TITAGARH","BDL","GRSE","HUDCO","NBCC","SJVN","IRCON","HFCL","TANLA","AFFLE","PRAJIND","TRIVENI","STERLITE","LATENTVIEW","ZENSAR","HAPPSTMNDS","ROUTE","INDIAMART","JUSTDIAL","NAZARA","POLICYBZR","CARTRADE","RATEGAIN","CAMPUS","BATAINDIA","RELAXO","KALYANKJIL","SENCO","KNRCON","PNCINFRA","HGINFRA","ASHOKA","JWL","TITAGARH","BEML","BDL","MAZAGON","COCHINSHIP","BSE","MCX","IEX","CDSL","CAMS"]

    all_syms = list(dict.fromkeys(LARGE+MID+SMALL))[:600]
    cat_map={k:"LARGE" for k in LARGE}
    cat_map.update({k:"MID" for k in MID})
    cat_map.update({k:"SMALL" for k in SMALL})
    print(f"FAST LIST: {len(all_syms)} Stocks")
    return all_syms, cat_map

def analyze(args):
    sym, obj, from_d, to_d, cat_map = args
    token=TOKEN_MAP.get(sym)
    if not token: return None
    try:
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not data or 'data' not in data or not data['data']: return None
        df=pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        if len(df)<25: return None
        df['ema9']=df['c'].ewm(span=9).mean()
        df['ema15']=df['c'].ewm(span=15).mean()
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
        delta=df['c'].diff()
        df['rsi']=100-(100/(1+(delta.where(delta>0,0).rolling(14).mean() / -delta.where(delta<0,0).rolling(14).mean())))
        df['macd']=df['c'].ewm(span=12).mean()-df['c'].ewm(span=26).mean()
        df['macd_sig']=df['macd'].ewm(span=9).mean()
        df['vol_avg']=df['v'].rolling(20).mean()
        df['atr']=(df['h']-df['l']).rolling(14).mean()
        last=df.iloc[-1]; prev=df.iloc[-2]
        ltp=last['c']; atr=last['atr'] if pd.notna(last['atr']) else ltp*0.007

        buy=0; sell=0; bc=[]; sc=[]
        if last['c']>last['o'] and prev['c']<prev['o']: buy+=1; bc.append("ENGULF")
        if last['c']<last['o'] and prev['c']>prev['o']: sell+=1; sc.append("ENGULF")
        if prev['ema9']<prev['ema15'] and last['ema9']>last['ema15']: buy+=1; bc.append("9x15UP")
        if prev['ema9']>prev['ema15'] and last['ema9']<last['ema15']: sell+=1; sc.append("9x15DN")
        if df['c'].iloc[-3:].is_monotonic_increasing: buy+=1; bc.append("3CBU")
        if df['c'].iloc[-3:].is_monotonic_decreasing: sell+=1; sc.append("3CBD")
        if last['ema9']>last['vwap']: buy+=1; bc.append("E9>V")
        if last['ema9']<last['vwap']: sell+=1; sc.append("E9<V")
        if last['rsi']>50: buy+=1; bc.append(f"RSI{int(last['rsi'])}")
        if last['rsi']<50: sell+=1; sc.append(f"RSI{int(last['rsi'])}")
        if last['macd']>last['macd_sig']: buy+=1; bc.append("MACD+")
        if last['macd']<last['macd_sig']: sell+=1; sc.append("MACD-")
        if last['v']>last['vol_avg']*0.5: buy+=0.5; sell+=0.5; bc.append("VOL"); sc.append("VOL")

        cat=cat_map.get(sym,"SMALL")
        thresh = 4
        if buy>=thresh:
            sl=round(min(df['l'].tail(5).min(), ltp-atr*1.2),1)
            return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp+atr*1.5,1),"t2":round(ltp+atr*3,1),"conds":bc}
        if sell>=thresh:
            sl=round(max(df['h'].tail(5).max(), ltp+atr*1.2),1)
            return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":sl,"t1":round(ltp-atr*1.5,1),"t2":round(ltp-atr*3,1),"conds":sc}
    except: return None
    return None

api_key=(os.getenv("ANGEL_API_KEY") or "").strip()
client_id=(os.getenv("ANGEL_CLIENT_ID") or "").strip()
pwd=(os.getenv("ANGEL_PASSWORD") or "").strip()
totp_secret=(os.getenv("ANGEL_TOTP_SECRET") or "").strip()
bot_token=(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
chat_id=(os.getenv("TELEGRAM_CHAT_ID") or "").strip()

obj=SmartConnect(api_key=api_key)
obj.generateSession(client_id,pwd,pyotp.TOTP(totp_secret).now())

today=datetime.now()
from_d=(today-timedelta(days=2)).strftime("%Y-%m-%d 09:15")
to_d=today.strftime("%Y-%m-%d 15:30")

all_syms, cat_map = get_1000_with_category()
state=load_state()

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    futs=[ex.submit(analyze,(s,obj,from_d,to_d,cat_map)) for s in all_syms]
    for f in concurrent.futures.as_completed(futs):
        r=f.result()
        if r: results.append(r)

def get_top(cat, side):
    filt=[x for x in results if x['cat']==cat and x['side']==side]
    return sorted(filt, key=lambda x: x['score'], reverse=True)[0] if filt else None

large_buy=get_top("LARGE","BUY")
large_sell=get_top("LARGE","SELL")
mid_buy=get_top("MID","BUY")
mid_sell=get_top("MID","SELL")
small_buy=get_top("SMALL","BUY")
small_sell=get_top("SMALL","SELL")

final_6 = [x for x in [large_buy, large_sell, mid_buy, mid_sell, small_buy, small_sell] if x]

pnl_history=load_pnl()
today_str=today.strftime("%Y-%m-%d")
active_prev=state.get("active",[])
active_now=[]
for a in active_prev:
    live = next((r for r in results if r['sym']==a.get('symbol')), None)
    if live:
        entry=a.get('price', live['ltp'])
        ltp_now=live['ltp']
        side=a.get('side','BUY')
        if side=='BUY': pnl = ltp_now - entry
        else: pnl = entry - ltp_now
        hit=""
        if side=='BUY':
            if ltp_now <= live['sl']: hit="SL HIT"
            elif ltp_now >= live['t1']: hit="T1 HIT"
        else:
            if ltp_now >= live['sl']: hit="SL HIT"
            elif ltp_now <= live['t1']: hit="T1 HIT"
        if hit:
            pnl_history.append({"date":today_str,"symbol":a.get('symbol'),"side":side,"entry":entry,"exit":ltp_now,"pnl":round(pnl,1),"result":hit,"time":today.strftime("%H:%M")})
        else:
            active_now.append(a)
    else:
        active_now.append(a)

save_pnl(pnl_history)

new_active=[]
for x in final_6[:2]:
    new_active.append({"symbol":x['sym'],"side":x['side'],"cat":x['cat'],"price":x['ltp'],"sl":x['sl'],"t1":x['t1'],"t2":x['t
