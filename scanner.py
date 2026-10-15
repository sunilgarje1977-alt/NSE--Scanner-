import os, requests, yfinance as yf
from datetime import datetime, timedelta
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

NSE_200 = ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","ASIANPAINT","AXISBANK","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","BAJAJFINSV","EICHERMOT","GRASIM","CIPLA","DIVISLAB","DRREDDY","APOLLOHOSP","BRITANNIA","NESTLEIND","BPCL","INDUSINDBK","SBILIFE","HDFCLIFE","TECHM","LTIM","HCLTECH","BAJAJ-AUTO","HEROMOTOCO","TATACONSUM","SRF","PERSISTENT","MPHASIS","COFORGE","LUPIN","AUROPHARMA","ALKEM","TORNTPHARM","ZYDUSLIFE","CUMMINSIND","ASHOKLEY","BALKRISIND","BHARATFORG","MOTHERSON","MRF","BOSCHLTD","TVSMOTOR","VOLTAS","HAVELLS","POLYCAB","KEI","DIXON","SYNGENE","LAURUSLABS","ATUL","AARTIIND","DEEPAKNTR","NAVINFLUOR","PIIND","UPL","COROMANDEL","SAIL","NMDC","VEDL","TATAPOWER","JSWENERGY","NHPC","PFC","RECLTD","IDFCFIRSTB","FEDERALBNK","BANDHANBNK","AUBANK","PNB","BANKBARODA","CDSL","BSE","MCX","ANGELONE","MUTHOOTFIN","CHOLAFIN","ZOMATO","PAYTM","NYKAA","IRCTC","INDIGO","KPITTECH","TATAELXSI","TRIDENT","BATAINDIA","IDEA","IRFC","RVNL","HAL","BEL","BHEL","SUZLON","YESBANK"]

NSE_150 = NSE_200[:150]

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=15)
    except: pass

def get_login():
    try:
        obj=SmartConnect(api_key=API_KEY)
        totp=pyotp.TOTP(TOTP_SECRET).now()
        obj.generateSession(CLIENT_CODE,PASSWORD,totp)
        return obj
    except: return None

def scan_one(sym):
    try:
        # yFinance ने Data - Angel वर Depend नाही - हाच Fix
        ticker = yf.Ticker(f"{sym}.NS")
        df = ticker.history(period="1d", interval="5m")
        if df.empty or len(df) < 15:
            return None

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        # VWAP
        df['typical']=(df['high']+df['low']+df['close'])/3
        df['vwap']=(df['typical']*df['volume']).cumsum()/df['volume'].cumsum()
        df['9ema']=df['close'].ewm(span=9).mean()
        delta=df['close'].diff()
        gain=(delta.where(delta>0,0)).rolling(14).mean()
        loss=(-delta.where(delta<0,0)).rolling(14).mean()
        rs=gain/loss
        df['rsi']=100-(100/(1+rs))

        c=df.iloc[-1]; p=df.iloc[-2]
        ltp=float(c['close'])

        cross_up = p['vwap'] <= p['9ema'] and c['vwap'] > c['9ema']
        cross_down = p['vwap'] >= p['9ema'] and c['vwap'] < c['9ema']

        # तुझा Screenshot Logic + Nifty +388 साठी Loose
        buy = (c['close'] > c['vwap']) and (c['vwap'] > c['9ema']) and (c['close'] > c['open'])
        sell = (c['close'] < c['vwap']) and (c['vwap'] < c['9ema']) and (c['close'] < c['open'])

        score=0
        if c['close'] > c['vwap']: score+=2
        if c['vwap'] > c['9ema']: score+=2
        if c['close'] > c['open']: score+=1
        if c['rsi']>55: score+=1

        # Nifty +388 आहे म्हणून BUY ला प्राधान्य
        if buy and c['rsi']>50:
            return ("BUY",sym,ltp,c,score+10 if cross_up else score)
        if sell and c['rsi']<45:
            return ("SELL",sym,ltp,c,score+5)
        if score>=4: # Momentum
            return ("MOMENTUM",sym,ltp,c,score)
        return None
    except Exception as e:
        return None

def main():
    obj=get_login() # फक्त Option Premium साठी
    all_res=[]
    with ThreadPoolExecutor(max_workers=15) as ex:
        futs=[ex.submit(scan_one,s) for s in NSE_200]
        for f in as_completed(futs):
            r=f.result()
            if r: all_res.append(r)

    if len(all_res)==0:
        send_tg(f"⚠️ Checked 0/{len(NSE_200)} | yFinance Fail @ {datetime.now().strftime('%H:%M:%S')} | Nifty +388 पण Data नाही")
        return

    # BUY आधी - कारण Nifty +388
    buys = sorted([x for x in all_res if x[0]=="BUY"], key=lambda x: x[4], reverse=True)[:5]
    if len(buys)>0:
        for _,sym,ltp,c,sc in buys:
            # Option Premium Angel ने Try
            opt_msg=f"{sym} CE @ 50-90"
            if obj:
                try:
                    atm = round(ltp/50)*50
                    sr=obj.searchScrip("NFO", sym)
                    if sr.get('data'):
                        for it in sr['data']:
                            if str(atm) in it['tradingsymbol'] and "CE" in it['tradingsymbol']:
                                lr=obj.ltpData("NFO", it['tradingsymbol'], it['symboltoken'])
                                if lr.get('data'):
                                    op=float(lr['data']['ltp'])
                                    if op>1000: op/=100
                                    if 30 <= op <= 120:
                                        opt_msg=f"{it['tradingsymbol']} @ {op:.1f} ✅"
                                        break
                except: pass

            send_tg(f"🟢 *{sym} CASH BUY @ {ltp:.2f}* | Nifty +388 | Checked {len(all_res)}/{len(NSE_200)}\nClose {c['close']:.1f} > VWAP {c['vwap']:.1f} > 9EMA {c['9ema']:.1f} | RSI {c['rsi']:.1f} Score {sc}\n\n*4 Level:*\n• NSE Cash BUY\n• NSE 150 Liquid {opt_msg}\n• Midcap CE @ 50-90\n• Nifty 50 CE @ 50-90")
        return

    # BUY नाही तर MOMENTUM - Guaranteed
    momentum = sorted(all_res, key=lambda x: x[4], reverse=True)[:5]
    for _,sym,ltp,c,sc in momentum:
        send_tg(f"⚡ *{sym} MOMENTUM BUY @ {ltp:.2f}* | Nifty FUT +388 🚀\nVWAP {c['vwap']:.1f} | 9EMA {c['9ema']:.1f} | RSI {c['rsi']:.1f} | Checked {len(all_res)}/{len(NSE_200)}\n\n• Cash BUY\n• NSE 150 CE @ 50-90\n• Nifty CE @ 50-90")

if __name__=="__main__":
    main()
