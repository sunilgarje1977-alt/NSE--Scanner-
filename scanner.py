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

NSE_200 = ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","ASIANPAINT","AXISBANK","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","BAJAJFINSV","EICHERMOT","GRASIM","CIPLA","DIVISLAB","DRREDDY","APOLLOHOSP","BRITANNIA","NESTLEIND","BPCL","INDUSINDBK","SBILIFE","HDFCLIFE","TECHM","LTIM","HCLTECH","BAJAJ-AUTO","HEROMOTOCO","TATACONSUM","SRF","PERSISTENT","MPHASIS","COFORGE","LUPIN","AUROPHARMA","ALKEM","TORNTPHARM","ZYDUSLIFE","CUMMINSIND","ASHOKLEY","BALKRISIND","BHARATFORG","MOTHERSON","MRF","BOSCHLTD","TVSMOTOR","VOLTAS","HAVELLS","POLYCAB","KEI","DIXON","SYNGENE","LAURUSLABS","ATUL","AARTIIND","DEEPAKNTR","NAVINFLUOR","PIIND","UPL","COROMANDEL","SAIL","NMDC","VEDL","TATAPOWER","JSWENERGY","NHPC","PFC","RECLTD","IDFCFIRSTB","FEDERALBNK","BANDHANBNK","AUBANK","PNB","BANKBARODA","CDSL","BSE","MCX","ANGELONE","MUTHOOTFIN","CHOLAFIN","ZOMATO","PAYTM","NYKAA","IRCTC","INDIGO","KPITTECH","TATAELXSI","TRIDENT","BATAINDIA","IDEA","IRFC","RVNL","HAL","BEL","BHEL","SUZLON","YESBANK","SULA","TATACHEM"]
NSE_150 = NSE_200[:150]

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass
def get_login():
    obj=SmartConnect(api_key=API_KEY); totp=pyotp.TOTP(TOTP_SECRET).now(); obj.generateSession(CLIENT_CODE,PASSWORD,totp); return obj

def get_option_premium(obj, stock, ltp, opt_type):
    try:
        atm = round(ltp/50)*50 if ltp>500 else round(ltp/10)*10
        strikes = [atm, atm+50, atm+100] if opt_type=="CE" else [atm, atm-50, atm-100]
        res=obj.searchScrip("NFO", stock)
        if not res.get('data'): return None
        for strike in strikes:
            for it in res['data']:
                if str(strike) in it['tradingsymbol'] and opt_type in it['tradingsymbol']:
                    lr=obj.ltpData("NFO", it['tradingsymbol'], it['symboltoken'])
                    if lr.get('data'):
                        op=float(lr['data']['ltp']); op=op/100 if op>1000 else op
                        if 40 <= op <= 110: return it['tradingsymbol'], op
        return None
    except: return None

def scan_one(args):
    obj, sym = args
    try:
        lr=obj.ltpData("NSE", sym, f"{sym}-EQ")
        if not lr.get('data'): return None
        ltp=float(lr['data']['ltp']);
        if ltp>10000: ltp/=100
        token=lr['data']['symboltoken']
        today=datetime.now().strftime("%Y-%m-%d")
        hp={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:15","todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        cd=obj.getCandleData(hp)
        if not cd.get('data') or len(cd['data'])<10: return None
        df=pd.DataFrame(cd['data'], columns=['time','open','high','low','close','volume'])
        for c in ['close','open','high','low','volume']: df[c]=pd.to_numeric(df[c])
        df['typical']=(df['high']+df['low']+df['close'])/3
        df['vwap']=(df['typical']*df['volume']).cumsum()/df['volume'].cumsum()
        df['9ema']=df['close'].ewm(span=9).mean()
        df['vol_avg']=df['volume'].rolling(10).mean()
        delta=df['close'].diff(); gain=(delta.where(delta>0,0)).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean(); rs=gain/loss; df['rsi']=100-(100/(1+rs))
        c=df.iloc[-1]; p=df.iloc[-2]

        cross_up = p['vwap'] <= p['9ema'] and c['vwap'] > c['9ema']
        cross_down = p['vwap'] >= p['9ema'] and c['vwap'] < c['9ema']

        # ===== FIXED LOGIC - RSI LOOSE 50-75 - Vol 1.0x =====
        buy_strict = (c['close'] > c['vwap']) and cross_up and (c['close'] > c['open']) and (c['volume'] > c['vol_avg']*1.0) and (50 <= c['rsi'] <= 75)
        sell_strict = (c['close'] < c['vwap']) and cross_down and (c['close'] < c['open']) and (c['volume'] > c['vol_avg']*1.0) and (35 <= c['rsi'] <= 55)

        # Score for fallback
        score = 0
        if c['close'] > c['vwap']: score+=1
        if c['vwap'] > c['9ema']: score+=1
        if c['close'] > c['open']: score+=1
        if c['rsi'] > 50: score+=1

        if buy_strict: return ("BUY_STRICT",sym,ltp,c,score)
        if sell_strict: return ("SELL_STRICT",sym,ltp,c,score)
        return ("MOMENTUM",sym,ltp,c,score) if score>=3 else None
    except: return None

def main():
    try: obj=get_login()
    except Exception as e: send_tg(f"❌ Login Fail {e}"); return
    all_res=[]
    with ThreadPoolExecutor(max_workers=15) as ex:
        futs=[ex.submit(scan_one,(obj,s)) for s in NSE_200]
        for f in as_completed(futs):
            r=f.result()
            if r: all_res.append(r)

    strict = [x for x in all_res if "STRICT" in x[0]]
    if len(strict) > 0:
        # Strict Signal मिळाले - हेच पाठव
        for typ,sym,ltp,c,sc in strict[:5]:
            opt_type="CE" if "BUY" in typ else "PE"
            opt=get_option_premium(obj,sym,ltp,opt_type) if sym in NSE_150 else None
            opt_line = f"NSE 150 Liquid {opt[0]} @ {opt[1]:.1f} (50-90)" if opt else f"NSE 150 Liquid {sym} {opt_type} @ 50-90"
            send_tg(f"🟢 *{sym} {'BUY' if 'BUY' in typ else 'SELL'} @ {ltp:.2f}*\nPrice>VWAP + VWAP Cross UP 9EMA + RSI {c['rsi']:.1f} ✅\n\n*4 Level:*\n• NSE Cash\n• {opt_line}\n• Mid/Smallcap {opt_type} @ 50-90\n• Nifty 50 {opt_type} @ 50-90")
    else:
        # Strict नाही - तर Top 3 Momentum पाठव - No Signal येणार नाही
        momentum = sorted([x for x in all_res if x[0]=="MOMENTUM"], key=lambda x: x[4], reverse=True)[:3]
        if len(momentum)>0:
            for _,sym,ltp,c,sc in momentum:
                opt=get_option_premium(obj,sym,ltp,"CE") if sym in NSE_150 else None
                opt_line = f"{opt[0]} @ {opt[1]:.1f}" if opt else f"{sym} CE @ 50-90"
                send_tg(f"⚡ *{sym} MOMENTUM BUY @ {ltp:.2f}*\nVWAP {c['vwap']:.2f} > 9EMA {c['9ema']:.2f} | RSI {c['rsi']:.1f} | Score {sc}/4\n\n• NSE Cash Momentum\n• NSE 150 Liquid {opt_line}\n• Nifty CE @ 50-90")
        else:
            send_tg(f"ℹ️ Checked {len(NSE_200)} | No Strict Cross (RSI 55-60 Tight) | Market RSI High")

if __name__=="__main__": main()
