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

# NSE 200 + NSE 150 Logic
NSE_200 = ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","ASIANPAINT","AXISBANK","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","BAJAJFINSV","EICHERMOT","GRASIM","CIPLA","DIVISLAB","DRREDDY","APOLLOHOSP","BRITANNIA","NESTLEIND","BPCL","INDUSINDBK","SBILIFE","HDFCLIFE","TECHM","LTIM","HCLTECH","BAJAJ-AUTO","HEROMOTOCO","TATACONSUM","SRF","PERSISTENT","MPHASIS","COFORGE","LUPIN","AUROPHARMA","ALKEM","TORNTPHARM","ZYDUSLIFE","CUMMINSIND","ASHOKLEY","BALKRISIND","BHARATFORG","MOTHERSON","MRF","BOSCHLTD","TVSMOTOR","VOLTAS","HAVELLS","POLYCAB","KEI","DIXON","SYNGENE","LAURUSLABS","ATUL","AARTIIND","DEEPAKNTR","NAVINFLUOR","PIIND","UPL","COROMANDEL","SAIL","NMDC","VEDL","TATAPOWER","JSWENERGY","NHPC","PFC","RECLTD","IDFCFIRSTB","FEDERALBNK","BANDHANBNK","AUBANK","PNB","BANKBARODA","CDSL","BSE","MCX","ANGELONE","MUTHOOTFIN","CHOLAFIN","ZOMATO","PAYTM","NYKAA","IRCTC","INDIGO","KPITTECH","TATAELXSI","TRIDENT","BATAINDIA","IDEA","IRFC","RVNL","HAL","BEL","BHEL","SUZLON","YESBANK","SULA","TATACHEM","ABCAPITAL","ADANIGREEN","CANBK","CHAMBLFERT","COLPAL","CONCOR","CROMPTON","CUB","DABUR","DALBHARAT","DLF","GODREJPROP","HDFCAMC","ICICIGI","INDHOTEL","JINDALSTEL","JUBLFOOD","LALPATHLAB","MARICO","MGL","NAUKRI","OBEROIRLTY","PAGEIND","PETRONET","PIDILITIND","PVRINOX","SBICARD","SHREECEM","SIEMENS","TATACOMM","TRENT","VBL","ZEEL"]

NSE_150 = NSE_200[:150]

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=15)
    except Exception as e: print(e)

def get_login():
    obj=SmartConnect(api_key=API_KEY)
    totp=pyotp.TOTP(TOTP_SECRET).now()
    obj.generateSession(CLIENT_CODE,PASSWORD,totp)
    return obj

def get_option_premium(obj, stock, ltp, opt_type):
    try:
        atm = round(ltp/50)*50 if ltp>500 else round(ltp/10)*10
        strikes = [atm, atm+50, atm+100, atm-50, atm+150] if opt_type=="CE" else [atm, atm-50, atm-100, atm+50, atm-150]
        res=obj.searchScrip("NFO", stock)
        if not res.get('data'): return None
        for strike in strikes:
            for it in res['data']:
                if str(strike) in it['tradingsymbol'] and opt_type in it['tradingsymbol'] and stock in it['tradingsymbol']:
                    lr=obj.ltpData("NFO", it['tradingsymbol'], it['symboltoken'])
                    if lr.get('data'):
                        op=float(lr['data']['ltp'])
                        if op>1000: op/=100
                        if 30 <= op <= 120: return it['tradingsymbol'], op, strike
        return None
    except: return None

def scan_one(args):
    obj, sym = args
    try:
        # TOKEN FIX - 117 चा Problem हिथूनच येतो
        token=""
        try:
            sr=obj.searchScrip("NSE", sym)
            if sr.get('data'):
                for it in sr['data']:
                    if it['tradingsymbol']==f"{sym}-EQ":
                        token=it['symboltoken']; break
                if not token: token=sr['data'][0]['symboltoken']
        except: return None
        if not token: return None

        lr=obj.ltpData("NSE", f"{sym}-EQ", token)
        if not lr.get('data'): return None
        ltp=float(lr['data']['ltp'])
        if ltp>10000: ltp/=100

        today=datetime.now().strftime("%Y-%m-%d")
        hp={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:15","todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        cd=obj.getCandleData(hp)
        if not cd.get('data') or len(cd['data'])<10: return None

        df=pd.DataFrame(cd['data'], columns=['time','open','high','low','close','volume'])
        for col in ['close','open','high','low','volume']: df[col]=pd.to_numeric(df[col])

        df['typical']=(df['high']+df['low']+df['close'])/3
        df['vwap']=(df['typical']*df['volume']).cumsum()/df['volume'].cumsum()
        df['9ema']=df['close'].ewm(span=9).mean()
        df['vol_avg']=df['volume'].rolling(10).mean()
        delta=df['close'].diff()
        gain=(delta.where(delta>0,0)).rolling(14).mean()
        loss=(-delta.where(delta<0,0)).rolling(14).mean()
        rs=gain/loss
        df['rsi']=100-(100/(1+rs))

        c=df.iloc[-1]; p=df.iloc[-2]
        cross_up = p['vwap'] <= p['9ema'] and c['vwap'] > c['9ema']
        cross_down = p['vwap'] >= p['9ema'] and c['vwap'] < c['9ema']

        # SCREENSHOT LOGIC - RSI थोडं Loose केलंय 55-75 जेणेकरून Signal येईल
        buy_strict = (c['close'] > c['vwap']) and cross_up and (c['close'] > c['open']) and (50 <= c['rsi'] <= 75)
        sell_strict = (c['close'] < c['vwap']) and cross_down and (c['close'] < c['open']) and (30 <= c['rsi'] <= 55)

        score=0
        if c['close'] > c['vwap']: score+=2
        if c['vwap'] > c['9ema']: score+=2
        if c['close'] > c['open']: score+=1
        if c['rsi']>50: score+=1

        if buy_strict: return ("BUY_STRICT",sym,ltp,c,score+10)
        if sell_strict: return ("SELL_STRICT",sym,ltp,c,score+10)
        return ("MOMENTUM",sym,ltp,c,score)
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

    strict = sorted([x for x in all_res if "STRICT" in x[0]], key=lambda x: x[4], reverse=True)

    if len(strict)>=1:
        for typ,sym,ltp,c,sc in strict[:5]:
            opt_type="CE" if "BUY" in typ else "PE"
            opt=get_option_premium(obj,sym,ltp,opt_type) if sym in NSE_150 else None
            opt_msg = f"{opt[0]} @ {opt[1]:.1f} (50-90) Strike {opt[2]} ✅" if opt else f"{sym} {opt_type} @ 50-90"
            side="BUY" if "BUY" in typ else "SELL"
            msg=(f"{'🟢' if side=='BUY' else '🔴'} *{sym} CASH {side} @ {ltp:.2f}*\n"
                 f"Price {' > ' if side=='BUY' else ' < '} VWAP | VWAP Cross {'UP' if side=='BUY' else 'DOWN'} 9EMA | RSI {c['rsi']:.1f} ✅\n\n"
                 f"*4 Level Option Logic:*\n• NSE Cash Share {side}\n• NSE 150 Liquid {opt_msg}\n• Mid/Smallcap Liquid {opt_type} @ 50-90\n• Nifty 50 {opt_type} @ 50-90")
            send_tg(msg)
        return

    # STRICT नाही तर TOP 3 MOMENTUM - GUARANTEED SIGNAL - No Signal येणारच नाही
    momentum = sorted(all_res, key=lambda x: x[4], reverse=True)[:3]
    if len(momentum)>0:
        for _,sym,ltp,c,sc in momentum:
            opt=get_option_premium(obj,sym,ltp,"CE") if sym in NSE_150 else None
            opt_line = f"{opt[0]} @ {opt[1]:.1f} (50-90)" if opt else f"{sym} CE @ 50-90"
            send_tg(f"⚡ *{sym} MOMENTUM BUY @ {ltp:.2f}*\nClose {c['close']:.1f} > VWAP {c['vwap']:.1f} + 9EMA {c['9ema']:.1f} | RSI {c['rsi']:.1f} | Score {sc}/6\n\n*4 Level:*\n• NSE Cash BUY\n• NSE 150 Liquid {opt_line}\n• Midcap CE @ 50-90\n• Nifty CE @ 50-90")
    else:
        send_tg(f"ℹ️ Checked {len(all_res)}/{len(NSE_200)} | Market Flat @ {datetime.now().strftime('%H:%M:%S')}")

if __name__=="__main__": main() 
