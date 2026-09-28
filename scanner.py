import requests, json, os, pyotp, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
from datetime import datetime, timedelta

STATE_FILE = "active_trades.json"

def load_state():
    if not os.path.exists(STATE_FILE): return {"active":[],"pending":[]}
    try:
        with open(STATE_FILE,'r') as f: return json.load(f)
    except: return {"active":[], "pending":[]}

def save_state(active, pending):
    with open(STATE_FILE,'w') as f: json.dump({"active":active,"pending":pending}, f)

def send_telegram(bot_token, chat_id, msg):
    try:
        requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", data={"chat_id":chat_id,"text":msg}, timeout=15)
    except Exception as e: print(e)

def get_token_map():
    try:
        url="https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        data=requests.get(url,timeout=20).json()
        mp={i['symbol'].replace('-EQ',''):i['token'] for i in data if i.get('exch_seg')=='NSE' and i.get('symbol')}
        return mp
    except: return {}

TOKEN_MAP=get_token_map()

def get_1000_with_category():
    headers={"User-Agent":"Mozilla/5.0"}
    s=requests.Session()
    try: s.get("https://www.nseindia.com",headers=headers,timeout=10)
    except: pass
    all_syms=[]; cat_map={}
    indices = [("NIFTY 100","LARGE"),("NIFTY 500","LARGE"),("NIFTY MIDCAP 150","MID"),("NIFTY SMALLCAP 250","SMALL"),("NIFTY MICROCAP 250","SMALL")]
    for idx_name, cat in indices:
        try:
            url=f"https://www.nseindia.com/api/equity-stockIndices?index={idx_name.replace(' ','%20')}"
            r=s.get(url,headers=headers,timeout=15).json()
            if 'data' in r:
                for d in r['data']:
                    sym=d['symbol']
                    if sym not in all_syms and d['lastPrice']>20:
                        all_syms.append(sym)
                        if sym not in cat_map: cat_map[sym]=cat
        except: continue
    all_syms=list(dict.fromkeys(all_syms))[:1000]
    return all_syms, cat_map

def analyze(args):
    sym, obj, from_d, to_d, cat_map = args
    token=TOKEN_MAP.get(sym)
    if not token: return None
    try:
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_d,"todate":to_d})
        if not data or 'data' not in data or not data['data']: return None
        df=pd.DataFrame(data['data'], columns=['ts','o','h','l','c','v'])
        if len(df)<30: return None
        df['ema9']=df['c'].ewm(span=9).mean()
        df['ema15']=df['c'].ewm(span=15).mean()
        df['vwap']=(df['c']*df['v']).cumsum()/df['v'].cumsum()
        delta=df['c'].diff()
        df['rsi']=100-(100/(1+(delta.where(delta>0,0).rolling(14).mean() / -delta.where(delta<0,0).rolling(14).mean())))
        df['st']= (df['c'] > df['c'].ewm(span=10).mean()).astype(int)
        df['macd']=df['c'].ewm(span=12).mean()-df['c'].ewm(span=26).mean()
        df['macd_sig']=df['macd'].ewm(span=9).mean()
        df['vol_avg']=df['v'].rolling(20).mean()
        df['atr']= (df['h']-df['l']).rolling(14).mean() # ATR for SL

        last=df.iloc[-1]; prev=df.iloc[-2]
        ltp=last['c']

        # --- SL TARGET CALCULATION ---
        atr = last['atr'] if pd.notna(last['atr']) else ltp*0.006
        recent_low = df['l'].tail(5).min()
        recent_high = df['h'].tail(5).max()

        buy=0; sell=0; bc=[]; sc=[]
        if last['c']>last['o'] and prev['c']<prev['o']: buy+=1; bc.append("ENGULF")
        if last['c']<last['o'] and prev['c']>prev['o']: sell+=1; sc.append("ENGULF")
        if prev['ema9']<prev['ema15'] and last['ema9']>last['ema15']: buy+=1; bc.append("9x15UP")
        if prev['ema9']>prev['ema15'] and last['ema9']<last['ema15']: sell+=1; sc.append("9x15DN")
        if df['c'].iloc[-3:].is_monotonic_increasing: buy+=1; bc.append("3CBU")
        if df['c'].iloc[-3:].is_monotonic_decreasing: sell+=1; sc.append("3CBD")
        if last['ema9']>last['vwap']: buy+=1; bc.append("E9>V")
        if last['ema9']<last['vwap']: sell+=1; sc.append("E9<V")
        if last['st']==1: buy+=1; bc.append("ST_G")
        if last['st']==0: sell+=1; sc.append("ST_R")
        if 40<last['rsi']<70: buy+=1; bc.append(f"RSI{int(last['rsi'])}")
        if 20<last['rsi']<60: sell+=1; sc.append(f"RSI{int(last['rsi'])}")
        if last['macd']>last['macd_sig']: buy+=1; bc.append("MACD+")
        if last['macd']<last['macd_sig']: sell+=1; sc.append("MACD-")
        if last['v']>last['vol_avg']*0.6: buy+=0.5; sell+=0.5

        cat=cat_map.get(sym,"SMALL")

        # SL TGT LOGIC - HINDALCO सारख्यासाठी
        if buy>=5:
            sl = min(recent_low, ltp - atr*1.2)
            sl = round(max(sl, ltp*0.988), 1) # max 1.2% SL
            t1 = round(ltp + atr*1.5, 1)
            t2 = round(ltp + atr*3, 1)
            return {"sym":sym,"side":"BUY","score":buy,"cat":cat,"ltp":ltp,"sl":sl,"t1":t1,"t2":t2,"conds":bc}
        if sell>=5:
            sl = max(recent_high, ltp + atr*1.2)
            sl = round(min(sl, ltp*1.012), 1) # max 1.2% SL
            t1 = round(ltp - atr*1.5, 1)
            t2 = round(ltp - atr*3, 1)
            return {"sym":sym,"side":"SELL","score":sell,"cat":cat,"ltp":ltp,"sl":sl,"t1":t1,"t2":t2,"conds":sc}
    except Exception as e:
        # print(f"{sym} err {e}")
        return None
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
save_state([{"symbol":x['sym'],"side":x['side'],"cat":x['cat']} for x in final_6[:2]], [{"symbol":x['sym'],"side":x['side'],"cat":x['cat']} for x in final_6[2:]])

# Telegram - आता HINDALCO ला SL TARGET येईल
msg=f"🎯 INTRADAY 6 TRADE | {today.strftime('%d %b %H:%M')} IST | 5Min\n"
msg+=f"Scan {len(all_syms)} | Signals {len(results)} | Active 2/2\n"
msg+=f"--------------------------------\n"
for x in final_6:
    per1 = round((x['t1']-x['ltp'])/x['ltp']*100, 1) if x['side']=='BUY' else round((x['ltp']-x['t1'])/x['ltp']*100, 1)
    per2 = round((x['t2']-x['ltp'])/x['ltp']*100, 1) if x['side']=='BUY' else round((x['ltp']-x['t2'])/x['ltp']*100, 1)
    msg+=f"{x['side']} {x['sym']}({x['cat']}) {x['score']}/8\nE:{x['ltp']:.1f} SL:{x['sl']:.1f} T1:{x['t1']}({per1}%) T2:{x['t2']}({per2}%)\n{','.join(x['conds'][:4])}\n\n"

send_telegram(bot_token, chat_id, msg)
print(msg)
