import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta

STATE_FILE = "active_trades.json"
PNL_FILE = "pnl_history.json"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"active":[],"pending":[]}
    try:
        with open(STATE_FILE,'r') as f:
            return json.load(f)
    except:
        return {"active":[],"pending":[]}

def save_state(active, pending):
    with open(STATE_FILE,'w') as f:
        json.dump({"active":active,"pending":pending}, f)

def load_pnl():
    if not os.path.exists(PNL_FILE):
        return []
    try:
        with open(PNL_FILE,'r') as f:
            return json.load(f)
    except:
        return []

def save_pnl(data):
    with open(PNL_FILE,'w') as f:
        json.dump(data,f)

def send_telegram(bot_token, chat_id, msg):
    try:
        if not bot_token or not chat_id:
            print("TELEGRAM SECRET MISSING")
            return
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={"chat_id":chat_id,"text":msg},
            timeout=15
        )
        print(f"Telegram Status: {r.status_code}")
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_token_map():
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data = requests.get(url,timeout=20).json()
        mp = {i['symbol'].replace('-EQ',''):i['token'] for i in data if i.get('exch_seg')=='NSE' and i.get('symbol')}
        return mp
    except:
        return {}

TOKEN_MAP = get_token_map()

def get_1000_with_category():
    LARGE = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","BEL","HAL","BSE","MCX","TATAPOWER","TATAMOTORS","WIPRO","TECHM","HCLTECH","GRASIM","CIPLA","DIVISLAB","DRREDDY","BRITANNIA","EICHERMOT","HEROMOTOCO","M&M","BAJAJ-AUTO","INDUSINDBK","SBILIFE","HDFCLIFE","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BHEL","NHPC","SJVN","NMDC","SAIL","VEDL","JSWENERGY","LICI","GAIL"]
    MID = ["BANKBARODA","PNB","CANBK","IDFCFIRSTB","BANDHANBNK","AUBANK","FEDERALBNK","CUB","RBLBANK","PNBHOUSING","MUTHOOTFIN","CHOLAFIN","M&MFIN","POONAWALLA","COFORGE","PERSISTENT","MPHASIS","KPITTECH","DIXON","KAYNES","POLYCAB","KEI","BSOFT","APOLLOHOSP","MAXHEALTH","FORTIS","AUROPHARMA","LUPIN","GODREJPROP","OBEROIRLTY","DLF","PIDILITIND","SRF","ATUL","AARTIIND","TATACHEM","CHAMBLFERT"]
    SMALL = ["ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","CDSL","ANGELONE","AFFLE","TEJASNET","HFCL","RAILTEL","IRCON","MAZAGON","GARDENREACH","COCHINSHIP","PRAJIND","JPOWER","TANLA","EASEMYTRIP","UCOBANK","IOB","MOTILALOFS","CAMS","KFINTECH","TATAINVEST","VBL","JWL","TITAGARH","BDL","GRSE","HUDCO","NBCC","PRAJIND","TRIVENI","LATENTVIEW","ZENSAR","ROUTE","INDIAMART","POLICYBZR","CAMPUS","BATAINDIA","KALYANKJIL","KNRCON","BEML","BSE","MCX"]

    all_syms = list(dict.fromkeys(LARGE+MID+SMALL))[:600]
    cat_map = {}
    for k in LARGE: cat_map[k]="LARGE"
    for k in MID: cat_map[k]="MID"
    for k in SMALL: cat_map[k]="SMALL"
    print(f"FAST LIST: {len(all_syms)} Stocks")
    return all_syms, cat_map

def analyze(args):
    sym, obj, from_d, to_d, cat_map = args
    token = TOKEN_MAP.get(sym)
    if not token:
        return None
    try:
        data = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not data or 'data' not in data or not data['data']:
            return None
        df = pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        if len(df)<25:
            return None
        df['ema9']=df['c'].ewm(span=9).mean()
        df['ema15']=df['c'].ewm(span=15).mean()
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
        delta=df['c'].diff()
        df['rsi']=100-(100/(1+(delta.where(delta>0,0).rolling(14).mean() / -delta.where(delta<0,0).rolling(14).mean())))
        df['macd']=df['c'].ewm(span=12).mean()-df['c'].ewm(span=26).mean()
        df['macd_sig']=df['macd'].ewm(span=9).mean()
        df['vol_avg']=df['v'].rolling(20).mean()
        df['atr']=(df['h']-df['l']).rolling(14).mean()
        last=df.iloc[-1]
        prev=df.iloc[-2]
        ltp=last['c']
        atr=last['atr'] if pd.notna(last['atr']) else ltp*0.007

        buy=0
        sell=0
        bc=[]
        sc=[]
        if last['c']>last['o'] and prev['c']<prev['o']:
            buy+=1; bc.append("ENGULF")
        if last['c']<last['o'] and prev['c']>prev['o']:
            sell+=1; sc.append("ENGULF")
        if prev['ema9']<prev['ema15'] and last['ema9']>last['ema15']:
            buy+=1; bc.append("9x15UP")
        if prev['ema9']>prev['ema15'] and last['ema9']<last['ema15']:
            sell+=1; sc.append("9x15DN")
        if df['c'].iloc[-3:].is_monotonic_increasing:
            buy+=1; bc.append("3CBU")
        if df['c'].iloc[-3:].is_monotonic_decreasing:
            sell+=1; sc.append("3CBD")
        if last['ema9']>last['vwap']:
            buy+=1; bc.append("E9>V")
        if last['ema9']<last['vwap']:
            sell+=1; sc.append("E9<V")
        if last['rsi']>50:
            buy+=1; bc.append(f"RSI{int(last['rsi'])}")
        if last['rsi']<50:
            sell+=1; sc.append(f"RSI{int(last['rsi'])}")
        if last['macd']>last['macd_sig']:
            buy+=1; bc.append("MACD+")
        if last['macd']<last['macd_sig']:
            sell+=1; sc.append("MACD-")
        if last['v']>last['vol_avg']*0.5:
            buy+=0.5; sell+=0.5; bc.append("VOL"); sc.append("VOL")

        cat=cat_map.get(sym,"SMALL")
        thresh=4
        if buy>=thresh:
            sl=round(min(df['l'].tail(5).min(), ltp-atr*1.2),1)
            t1=round(ltp+atr*1.5,1)
            t2=round(ltp+atr*3,1)
            return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":sl,"t1":t1,"t2":t2,"conds":bc}
        if sell>=thresh:
            sl=round(max(df['h'].tail(5).max(), ltp+atr*1.2),1)
            t1=round(ltp-atr*1.5,1)
            t2=round(ltp-atr*3,1)
            return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":sl,"t1":t1,"t2":t2,"conds":sc}
    except:
        return None
    return None

api_key=(os.getenv("ANGEL_API_KEY") or "").strip()
client_id=(os.getenv("ANGEL_CLIENT_ID") or "").strip()
pwd=(os.getenv("ANGEL_PASSWORD") or "").strip()
totp_secret=(os.getenv("ANGEL_TOTP_SECRET") or "").strip()
bot_token=(os.getenv
