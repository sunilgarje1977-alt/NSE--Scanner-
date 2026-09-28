
import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta

STATE_FILE = "active_trades.json"

def load_state():
    if not os.path.exists(STATE_FILE): return {"active":[], "pending":[]}
    try:
        with open(STATE_FILE,'r') as f: return json.load(f)
    except: return {"active":[], "pending":[]}

def save_state(active, pending):
    with open(STATE_FILE,'w') as f: json.dump({"active":active,"pending":pending}, f)

def send_telegram(bot_token, chat_id, msg):
    try:
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data={"chat_id":chat_id,"text":msg}, timeout=15)
    except: pass

def get_token_map():
    try:
        url="https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data=requests.get(url,timeout=20).json()
        mp={i['symbol'].replace('-EQ',''):i['token'] for i in data if i.get('exch_seg')=='NSE' and i.get('symbol')}
        return mp
    except: return {}

TOKEN_MAP=get_token_map()

# MID + SMALL चे Permanent List - NSE API Fail झाला तरी येईल
MID_PERM = ["BANKBARODA","PNB","CANBK","IDFCFIRSTB","BANDHANBNK","AUBANK","FEDERALBNK","CUB","KARURVYSYA","RBLBANK","PNBHOUSING","MUTHOOTFIN","MANAPPURAM","CHOLAFIN","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BEL","HAL","BDL","BHEL","CONCOR","NHPC","SJVN","COALINDIA","NMDC","SAIL","HINDZINC","VEDL","JINDALSTEL","JSWENERGY","TATAPOWER","TATAELXSI","COFORGE","PERSISTENT","MPHASIS","KPITTECH","TATAELXSI","DIXON","KAYNES","AMBER","POLYCAB","KEI","LTIM","BSOFT"]
SMALL_PERM = ["ZOMATO","PAYTM","NYKAA","DELHIVERY","IDEA","YESBANK","SUZLON","IEX","CDSL","BSE","MCX","ANGELONE","MOTILALOFS","CAMS","KFINTECH","KPITTECH","TEJASNET","HFCL","STERLITE","RAILTEL","IRCON","MAZAGON","GARDENREACH","COCHINSHIP","PRAJIND","TRIVENI","JPOWER","RENUKA","BALRAMCHIN","TATACHEM","CHAMBLFERT","DEEPAKNTR","AARTIIND","ATUL","VINATIORG","NAVINCORP","TANLA","AFFLE","LATENTVIEW","EASEMYTRIP","CENTRALBK","UCOBANK","IOB","MAHABANK","UNIONBANK"]

def get_1000_with_category():
    headers={"User-Agent":"Mozilla/5.0"}
    s=requests.Session()
    try: s.get("https://www.nseindia.com",headers=headers,timeout=10)
    except: pass

    all_syms=[]
    cat_map={}

    # LARGE
    for idx in ["NIFTY 100","NIFTY 500"]:
        try:
            url=f"https://www.nseindia.com/api/equity-stockIndices?index={idx.replace(' ','%20')}"
            r=s.get(url,headers=headers,timeout=15).json()
            if 'data' in r:
                for d in r['data']:
                    sym=d['symbol']
                    if sym not in all_syms and d['lastPrice']>20:
                        all_syms.append(sym)
                        if sym not in cat_map: cat_map[sym]="LARGE"
        except: pass

    # MID - Permanent + NSE
    try:
        url="https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20MIDCAP%20150"
        r=s.get(url,headers=headers,timeout=15).json()
        if 'data' in r:
            for d in r['data']:
                sym=d['symbol']
                if sym not in all_syms:
                    all_syms.append(sym)
                    cat_map[sym]="MID"
    except: pass
    for sym in MID_PERM:
        if sym not in all_syms: all_syms.append(sym)
        if sym not in cat_map: cat_map[sym]="MID"

    # SMALL - Permanent + NSE
    try:
        for idx in ["NIFTY SMALLCAP 250","NIFTY MICROCAP 250"]:
            url=f"https://www.nseindia.com/api/equity-stockIndices?index={idx.replace(' ','%20')}"
            r=s.get(url,headers=headers,timeout=15).json()
            if 'data' in r:
                for d in r['data']:
                    sym=d['symbol']
                    if sym not in all_syms and d['lastPrice']>20:
                        all_syms.append(sym)
                        if sym not in cat_map: cat_map[sym]="SMALL"
    except: pass
    for sym in SMALL_PERM:
        if sym not in all_syms: all_syms.append(sym)
        if sym not in cat_map: cat_map[sym]="SMALL"

    # Balance: 200 Large + 200 Mid + 600 Small = 1000
    all_syms=list(dict.fromkeys(all_syms))[:1000]
    large_n = len([k for k,v in cat_map.items() if v=="LARGE"])
    mid_n = len([k for k,v in cat_map.items() if v=="MID"])
    small_n = len([k for k,v in cat_map.items() if v=="SMALL"])
    print(f"1000 LIST FINAL: {len(all_syms)} | LARGE {large_n} | MID {mid_n} | SMALL {small_n}")
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
        # MID/SMALL साठी Threshold कमी - 3.5
        thresh = 5 if cat=="LARGE" else 3.5

        if buy>=thresh:
            sl=round(min(df['l'].tail(5).min(), ltp-atr*1.2),1)
            return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":round(sl,1),"t1":round(ltp+atr*1.5,1),"t2":round(ltp+atr*3,1),"conds":bc}
        if sell>=thresh:
            sl=round(max(df['h'].tail(5).max(), ltp+atr*1.2),1)
            return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":round(sl,1),"t1":round(ltp-atr*1.5,1),"t2":round(ltp-atr*3,1),"conds":sc}
    except: return None
    return None

# MAIN
api_key=(os.getenv("ANGEL_API_KEY") or "").strip()
client_id=(os.getenv("ANGEL_CLIENT_ID") or "").strip()
pwd=(os.getenv("ANGEL_PASSWORD") or "").strip()
totp_secret=(os.getenv("ANGEL_TOTP_SECRET") or "").strip()
bot_token=(os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
chat_id=(os.getenv("TELEGRAM_CHAT_ID") or "").strip()

obj=SmartConnect(api_key=api_key)
obj.generateSession(client_id,pwd,pyotp.TOTP(totp_secret).now())

today=datetime.now()
from_d=(today-timedelta(days=5)).strftime("%Y-%m-%d 09:15")
to_d=today.strftime("%Y-%m-%d 15:30")

all_syms, cat_map = get_1000_with_category()

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
    futs=[ex.submit(analyze,(s,obj,from_d,to_d,cat_map)) for s in all_syms]
    for f in concurrent.futures.as_completed(futs):
        r=f.result()
        if r: results.append(r)

print(f"Signals Found: {len(results)}")

def get_top(cat, side):
    filt=[x for x in results if x['cat']==cat and x['side']==side]
    return sorted(filt, key=lambda x: x['score'], reverse=True)[0] if filt else None

# GUARANTEED 6 - प्रत्येक Cat मधून 1 BUY 1 SELL
large_buy=get_top("LARGE","BUY")
large_sell=get_top("LARGE","SELL")
mid_buy=get_top("MID","BUY")
mid_sell=get_top("MID","SELL")
small_buy=get_top("SMALL","BUY")
small_sell=get_top("SMALL","SELL")

final_6 = [x for x in [large_buy, large_sell, mid_buy, mid_sell, small_buy, small_sell] if x]

save_state([{"symbol":x['sym'],"side":x['side'],"cat":x['cat']} for x in final_6[:2]], [{"symbol":x['sym'],"side":x['side'],"cat":x['cat']} for x in final_6[2:]])

msg=f"🎯 INTRADAY 6 TRADE | {today.strftime('%d %b %H:%M')} IST | 5Min\n"
msg+=f"Scan {len(all_syms)} | L:{len([x for x in results if x['cat']=='LARGE'])} M:{len([x for x in results if x['cat']=='MID'])} S:{len([x for x in results if x['cat']=='SMALL'])}\n"
msg+=f"--------------------------------\n"
for x in final_6:
    msg+=f"{x['side']} {x['sym']}({x['cat']}) {x['score']}/8\nE:{x['ltp']:.1f} SL:{x['sl']:.1f} T1:{x['t1']} T2:{x['t2']}\n{','.join(x['conds'][:3])}\n\n"

if not final_6:
    msg+= "No Setup Found - Next 5Min"

send_telegram(bot_token, chat_id, msg)
print(msg)
