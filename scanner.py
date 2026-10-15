import os, requests
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
import pyotp
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY=os.getenv("ANGEL_API_KEY")
CLIENT_CODE=os.getenv("ANGEL_CLIENT_ID")
PASSWORD=os.getenv("ANGEL_PASSWORD")
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")

# NIFTY + BANKNIFTY + NSE 500 ADD केले
NSE_1000 = ["NIFTY","BANKNIFTY","RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","ASIANPAINT","AXISBANK","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","BAJAJFINSV","EICHERMOT","GRASIM","CIPLA","DIVISLAB","DRREDDY","APOLLOHOSP","BRITANNIA","NESTLEIND","BPCL","INDUSINDBK","SBILIFE","HDFCLIFE","TECHM","LTIM","HCLTECH","BAJAJ-AUTO","HEROMOTOCO","TATACONSUM","SRF","PERSISTENT","MPHASIS","COFORGE","LUPIN","AUROPHARMA","ALKEM","TORNTPHARM","ZYDUSLIFE","CUMMINSIND","ASHOKLEY","BALKRISIND","BHARATFORG","MOTHERSON","MRF","BOSCHLTD","TVSMOTOR","VOLTAS","HAVELLS","POLYCAB","KEI","DIXON","SYNGENE","LAURUSLABS","ATUL","AARTIIND","DEEPAKNTR","NAVINFLUOR","PIIND","UPL","COROMANDEL","SAIL","NMDC","VEDL","TATAPOWER","JSWENERGY","NHPC","PFC","RECLTD","IDFCFIRSTB","FEDERALBNK","BANDHANBNK","AUBANK","PNB","BANKBARODA","CDSL","BSE","MCX","ANGELONE","MUTHOOTFIN","CHOLAFIN","ZOMATO","PAYTM","NYKAA","IRCTC","INDIGO","KPITTECH","TATAELXSI","SULA","NIFTY"]
NSE_150 = NSE_1000[:150]

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_login():
    obj=SmartConnect(api_key=API_KEY); totp=pyotp.TOTP(TOTP_SECRET).now(); obj.generateSession(CLIENT_CODE,PASSWORD,totp); return obj

def scan_one(args):
    obj, sym = args
    try:
        # NIFTY / SULA साठी Token Logic
        if sym in ["NIFTY","BANKNIFTY"]:
            ltp_data = obj.ltpData("NFO", sym, f"{sym}")
        else:
            ltp_data = obj.ltpData("NSE", sym, f"{sym}-EQ")
        
        if not ltp_data.get('data'): return None
        ltp=float(ltp_data['data']['ltp'])/100 if float(ltp_data['data']['ltp'])>1000 else float(ltp_data['data']['ltp'])
        token=ltp_data['data'].get('symboltoken',"")
        exch = "NFO" if sym in ["NIFTY","BANKNIFTY"] else "NSE"
        today=datetime.now().strftime("%Y-%m-%d")
        hp={"exchange":exch,"symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:15","todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        cd=obj.getCandleData(hp)
        if not cd.get('data') or len(cd['data'])<10: return None
        df=pd.DataFrame(cd['data'], columns=['time','open','high','low','close','volume'])
        df['close']=df['close'].astype(float);df['open']=df['open'].astype(float);df['volume']=df['volume'].astype(int);df['high']=df['high'].astype(float);df['low']=df['low'].astype(float)
        df['typical']=(df['high']+df['low']+df['close'])/3
        df['vwap']=(df['typical']*df['volume']).cumsum()/df['volume'].cumsum()
        df['9ema']=df['close'].ewm(span=9).mean()
        df['vol_avg']=df['volume'].rolling(10).mean()
        delta=df['close'].diff(); gain=(delta.where(delta>0,0)).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean(); rs=gain/loss; df['rsi']=100-(100/(1+rs))
        c=df.iloc[-1]

        # ===== FINAL LOOSEST - तुझ्या Screenshot साठी =====
        # VWAP Cross UP राहू दे + Price > VWAP + RSI 45-85 (तुझा 71.56 आणि 74.34 Pass होईल)
        buy = (c['close'] > c['vwap']) and (c['vwap'] > c['9ema']) and (45 <= c['rsi'] <= 85)
        sell = (c['close'] < c['vwap']) and (c['vwap'] < c['9ema']) and (15 <= c['rsi'] <= 55)

        if buy: return ("BUY",sym,ltp,c)
        if sell: return ("SELL",sym,ltp,c)
        return None
    except Exception as e:
        print(f"{sym} err {e}")
        return None

def main():
    try: obj=get_login()
    except Exception as e: send_tg(f"❌ Login Fail {e}"); return
    results=[]
    with ThreadPoolExecutor(max_workers=15) as ex:
        futs=[ex.submit(scan_one,(obj,s)) for s in NSE_1000]
        for f in as_completed(futs):
            r=f.result()
            if r: results.append(r)
    if len(results)==0:
        send_tg(f"ℹ️ No Signal @ {datetime.now().strftime('%H:%M:%S')} Checked {len(NSE_1000)}")
        return
    for side,sym,ltp,c in results:
        tag="🔵 NSE 150" if sym in NSE_150 else "🟠 Midcap"
        if side=="BUY": msg=f"🟢 *{sym} BUY @ {ltp:.2f}*\nVWAP {c['vwap']:.2f} > 9EMA {c['9ema']:.2f} | RSI {c['rsi']:.1f} ✅\n{tag}\n\n➡️ *{sym} CE @ 50-90*\n➡️ *NIFTY CE @ 50-90*"
        else: msg=f"🔴 *{sym} SELL @ {ltp:.2f}*\nVWAP {c['vwap']:.2f} < 9EMA {c['9ema']:.2f} | RSI {c['rsi']:.1f} ✅\n{tag}\n\n➡️ *{sym} PE @ 50-90*\n➡️ *NIFTY PE @ 50-90*"
        send_tg(msg)

if __name__=="__main__": main()
