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
            print("SECRET MISSING")
            return
        url = "https://api.telegram.org/bot" + bot_token + "/sendMessage"
        r = requests.post(url, data={"chat_id":chat_id,"text":msg}, timeout=15)
        print("Telegram:", r.status_code)
    except Exception as e:
        print("Tg Error", e)

def get_token_map():
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data = requests.get(url, timeout=20).json()
        mp = {}
        for i in data:
            if i.get('exch_seg') == 'NSE' and i.get('symbol'):
                mp[i['symbol'].replace('-EQ','')] = i['token']
        return mp
    except:
        return {}

TOKEN_MAP = get_token_map()

def get_list():
    LARGE = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","BEL","HAL","BSE","MCX","TATAPOWER","TATAMOTORS","WIPRO","TECHM","HCLTECH","GRASIM","CIPLA","DIVISLAB","BRITANNIA","M&M","BAJAJ-AUTO","INDUSINDBK","SBILIFE","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","HAL","BEML","BHEL","NHPC","SJVN","NMDC","SAIL","VEDL","LICI","GAIL"]
    MID = ["BANKBARODA","PNB","CANBK","IDFCFIRSTB","BANDHANBNK","AUBANK","FEDERALBNK","CUB","RBLBANK","PNBHOUSING","MUTHOOTFIN","CHOLAFIN","COFORGE","PERSISTENT","MPHASIS","KPITTECH","DIXON","KAYNES","POLYCAB","KEI","BSOFT","APOLLOHOSP","MAXHEALTH","FORTIS","AUROPHARMA","LUPIN","GODREJPROP","DLF","PIDILITIND","SRF","TATACHEM"]
    SMALL = ["ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","CDSL","ANGELONE","AFFLE","TEJASNET","HFCL","RAILTEL","IRCON","MAZAGON","COCHINSHIP","PRAJIND","TANLA","EASEMYTRIP","UCOBANK","IOB","CAMS","KFINTECH","TATAINVEST","VBL","JWL","TITAGARH","BDL","GRSE","HUDCO","NBCC","LATENTVIEW","ZENSAR","ROUTE","BSE","MCX"]
    all_syms = LARGE + MID + SMALL
    all_syms = list(dict.fromkeys(all_syms))[:600]
    cat_map = {}
    for k in LARGE: cat_map[k]="LARGE"
    for k in MID: cat_map[k]="MID"
    for k in SMALL: cat_map[k]="SMALL"
    return all_syms, cat_map

def analyze(args):
    sym, obj, from_d, to_d, cat_map = args
    token = TOKEN_MAP.get(sym)
    if not token: return None
    try:
        candle = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not candle or 'data' not in candle: return None
        if not candle['data']: return None
        df = pd.DataFrame(candle['data'], columns=['ts','o','h','l','c','v'])
        if len(df) < 25: return None
        df['ema9'] = df['c'].ewm(span=9).mean()
        df['ema15'] = df['c'].ewm(span=15).mean()
        df['vwap'] = (df['c']*df['v']).cumsum() / df['v'].cumsum()
        delta = df['c'].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + gain/loss))
        df['macd'] = df['c'].ewm(span=12).mean() - df['c'].ewm(span=26).mean()
        df['macd_sig'] = df['macd'].ewm(span=9).mean()
        df['vol_avg'] = df['v'].rolling(20).mean()
        df['atr'] = (df['h']-df['l']).rolling(14).mean()
        last = df.iloc[-1]
        prev = df.iloc[-2]
        ltp = last['c']
        atr = last['atr']
        if pd.isna(atr): atr = ltp * 0.007

        buy=0; sell=0; bc=[]; sc=[]
        if last['c']>last['o'] and prev['c']<prev['o']: buy+=1; bc.append("ENGULF")
        if last['c']<last['o'] and prev['c']>prev['o']: sell+=1; sc.append("ENGULF")
        if prev['ema9']<prev['ema15'] and last['ema9']>last['ema15']: buy+=1; bc.append("9x15UP")
        if prev['ema9']>prev['ema15'] and last['ema9']<last['ema15']: sell+=1; sc.append("9x15DN")
        if df['c'].iloc[-3:].is_monotonic_increasing: buy+=1; bc.append("3CBU")
        if df['c'].iloc[-3:].is_monotonic_decreasing: sell+=1; sc.append("3CBD")
        if last['ema9']>last['vwap']: buy+=1; bc.append("E9>V")
        if last['ema9']<last['vwap']: sell+=1; sc.append("E9<V")
        if last['rsi']>50: buy+=1; bc.append("RSI")
        if last['rsi']<50: sell+=1; sc.append("RSI")
        if last['macd']>last['macd_sig']: buy+=1; bc.append("MACD+")
        if last['macd']<last['macd_sig']: sell+=1; sc.append("MACD-")
        if last['v']>last['vol_avg']*0.5: buy+=0.5; sell+=0.5

        cat = cat_map.get(sym,"SMALL")
        if buy>=4:
            sl = round(min(df['l'].tail(5).min(), ltp-atr*1.2),1)
            t1 = round(ltp+atr*1.5,1)
            t2 = round(ltp+atr*3,1)
            return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":sl,"t1":t1,"t2":t2,"conds":bc}
        if sell>=4:
            sl = round(max(df['h'].tail(5).max(), ltp+atr*1.2),1)
            t1 = round(ltp-atr*1.5,1)
            t2 = round(ltp-atr*3,1)
            return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":sl,"t1":t1,"t2":t2,"conds":sc}
    except:
        return None
    return None

api_key = os.getenv("ANGEL_API_KEY","").strip()
client_id = os.getenv("ANGEL_CLIENT_ID","").strip()
pwd = os.getenv("ANGEL_PASSWORD","").strip()
totp_secret = os.getenv("ANGEL_TOTP_SECRET","").strip()
bot_token = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
chat_id = os.getenv("TELEGRAM_CHAT_ID","").strip()

obj = SmartConnect(api_key=api_key)
obj.generateSession(client_id, pwd, pyotp.TOTP(totp_secret).now())

today = datetime.now()
from_d = (today - timedelta(days=2)).strftime("%Y-%m-%d 09:15")
to_d = today.strftime("%Y-%m-%d 15:30")

all_syms, cat_map = get_list()
state = load_state()

results = []
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    futs = [ex.submit(analyze, (s,obj,from_d,to_d,cat_map)) for s in all_syms]
    for f in concurrent.futures.as_completed(futs):
        r = f.result()
        if r: results.append(r)

def get_top(cat, side):
    filt = [x for x in results if x['cat']==cat and x['side']==side]
    if not filt: return None
    filt = sorted(filt, key=lambda x: x['score'], reverse=True)
    return filt[0]

large_buy = get_top("LARGE","BUY")
large_sell = get_top("LARGE","SELL")
mid_buy = get_top("MID","BUY")
mid_sell = get_top("MID","SELL")
small_buy = get_top("SMALL","BUY")
small_sell = get_top("SMALL","SELL")

final_6 = []
for x in [large_buy, large_sell, mid_buy, mid_sell, small_buy, small_sell]:
    if x: final_6.append(x)

pnl_history = load_pnl()
today_str = today.strftime("%Y-%m-%d")

new_active = []
for x in final_6[:2]:
    new_active.append({"symbol":x["sym"],"side":x["side"],"cat":x["cat"],"price":x["ltp"],"sl":x["sl"],"t1":x["t1"],"t2":x["t2"],"time":today.strftime("%H:%M")})

pending_list = []
for x in final_6[2:]:
    pending_list.append({"symbol":x["sym"],"side":x["side"],"cat":x["cat"],"price":x["ltp"],"sl":x["sl"],"t1":x["t1"],"t2":x["t2"]})

save_state(new_active, pending_list)
save_pnl(pnl_history)

msg = "🎯 INTRADAY 6 TRADE | " + today.strftime("%d %b %H:%M") + " IST | 5Min\n"
msg = msg + f"Scan {len(all_syms)} | Found {len(results)}\n"
msg = msg + "--------------------------------\n"

if final_6:
    for x in final_6:
        cond_str = ','.join(x['conds'][:4])
        line1 = f"{x['side']} {x['sym']}({x['cat']}) {x['score']}/8\n"
        line2 = f"E:{x['ltp']:.1f} SL:{x['sl']:.1f} T1:{x['t1']} T2:{x['t2']}\n"
        msg = msg + line1 + line2 + cond_str + "\n\n"
else:
    msg = msg + "No Signal Found\n\n"

msg = msg + "--------------------------------\n"
msg = msg + f"📊 P&L {today.strftime('%d %b')}\n"
active_str = ', '.join([a['symbol'] for a in new_active])
msg = msg + f"Active: {active_str}\n"

send_telegram(bot_token, chat_id, msg)
print(msg)
