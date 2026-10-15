import os, requests, time
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

# 200 Valid NSE Stocks - सगळे Valid - NIFTY काढला
NSE_200 = ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","ASIANPAINT","AXISBANK","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","BAJAJFINSV","EICHERMOT","GRASIM","CIPLA","DIVISLAB","DRREDDY","APOLLOHOSP","BRITANNIA","NESTLEIND","BPCL","INDUSINDBK","SBILIFE","HDFCLIFE","TECHM","LTIM","HCLTECH","BAJAJ-AUTO","HEROMOTOCO","TATACONSUM","SRF","PERSISTENT","MPHASIS","COFORGE","LUPIN","AUROPHARMA","ALKEM","TORNTPHARM","ZYDUSLIFE","CUMMINSIND","ASHOKLEY","BALKRISIND","BHARATFORG","MOTHERSON","MRF","BOSCHLTD","TVSMOTOR","VOLTAS","HAVELLS","POLYCAB","KEI","DIXON","SYNGENE","LAURUSLABS","ATUL","AARTIIND","DEEPAKNTR","NAVINFLUOR","PIIND","UPL","COROMANDEL","SAIL","NMDC","VEDL","TATAPOWER","JSWENERGY","NHPC","PFC","RECLTD","IDFCFIRSTB","FEDERALBNK","BANDHANBNK","AUBANK","PNB","BANKBARODA","CDSL","BSE","MCX","ANGELONE","MUTHOOTFIN","CHOLAFIN","ZOMATO","PAYTM","NYKAA","IRCTC","INDIGO","KPITTECH","TATAELXSI","TRIDENT","BATAINDIA","IDEA","IRFC","RVNL","HAL","BEL","BHEL","SUZLON","YESBANK","SULA","TATACHEM","ABCAPITAL","ABFRL","ADANIGREEN","ADANIPOWER","ATGL","BANKINDIA","BERGEPAINT","BIOCON","CANBK","CHAMBLFERT","COLPAL","CONCOR","CROMPTON","CUB","DABUR","DALBHARAT","DLF","ESCORTS","EXIDEIND","GODREJPROP","GRANULES","GSPL","GUJGASLTD","HDFCAMC","ICICIGI","INDHOTEL","INDIAMART","INDIANB","INDUSTOWER","IPCALAB","JINDALSTEL","JKCEMENT","JUBLFOOD","LALPATHLAB","LICHSGFIN","M&MFIN","MANAPPURAM","MARICO","MCDOWELL-N","MFSL","MGL","NAM-INDIA","NATIONALUM","NAUKRI","OBEROIRLTY","OFSS","PAGEIND","PEL","PETRONET","PFIZER","PIDILITIND","PVRINOX","RAMCOCEM","RBLBANK","SBICARD","SHREECEM","SIEMENS","STAR","SUNTECK","TATACOMM","TRENT","UBL","UNITSPIRITS","VBL","ZEEL","TATAPOWER","RELIANCE","INFY"]
NSE_150 = NSE_200[:150]

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def get_login():
    obj=SmartConnect(api_key=API_KEY); totp=pyotp.TOTP(TOTP_SECRET).now(); obj.generateSession(CLIENT_CODE,PASSWORD,totp); return obj

def scan_one(args):
    obj, sym = args
    try:
        lr=obj.ltpData("NSE", sym, f"{sym}-EQ")
        if not lr.get('data') or not lr['data'].get('symboltoken'): return None
        ltp=float(lr['data']['ltp'])
        if ltp>10000: ltp=ltp/100
        token=lr['data'].get('symboltoken',"")
        today=datetime.now().strftime("%Y-%m-%d")
        hp={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:15","todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        cd=obj.getCandleData(hp)
        if not cd.get('data') or len(cd['data'])<10: return None
        df=pd.DataFrame(cd['data'], columns=['time','open','high','low','close','volume'])
        for col in ['close','open','volume','high','low']: df[col]=pd.to_numeric(df[col])
        df['typical']=(df['high']+df['low']+df['close'])/3
        df['vwap']=(df['typical']*df['volume']).cumsum()/df['volume'].cumsum()
        df['9ema']=df['close'].ewm(span=9).mean()
        delta=df['close'].diff(); gain=(delta.where(delta>0,0)).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean(); rs=gain/loss; df['rsi']=100-(100/(1+rs))
        c=df.iloc[-1]
        # LOOSEST BUY SELL - दोन्ही
        buy = (c['close'] > c['vwap']) and (c['vwap'] > c['9ema']) and (40 <= c['rsi'] <= 90)
        sell = (c['close'] < c['vwap']) and (c['vwap'] < c['9ema']) and (10 <= c['rsi'] <= 60)
        if buy: return ("BUY",sym,ltp,c)
        if sell: return ("SELL",sym,ltp,c)
        return None
    except: return None

def main():
    try: obj=get_login()
    except Exception as e: send_tg(f"❌ Login Fail {e}"); return
    results=[]
    with ThreadPoolExecutor(max_workers=15) as ex:
        futs=[ex.submit(scan_one,(obj,s)) for s in NSE_200]
        for f in as_completed(futs):
            r=f.result()
            if r: results.append(r)
    if len(results)==0:
        send_tg(f"ℹ️ No Signal @ {datetime.now().strftime('%H:%M:%S')} Checked {len(NSE_200)} | VWAP > 9EMA + RSI 40-90 Active")
        return
    for side,sym,ltp,c in results:
        tag="🔵 NSE 150" if sym in NSE_150 else "🟠 Midcap"
        if side=="BUY": msg=f"🟢 *{sym} BUY @ {ltp:.2f}*\nVWAP {c['vwap']:.2f} > 9EMA {c['9ema']:.2f} Cross | RSI {c['rsi']:.1f} ✅\n{tag}\n\n➡️ *{sym} CE @ 50-90*\n➡️ *NIFTY CE @ 50-90*"
        else: msg=f"🔴 *{sym} SELL @ {ltp:.2f}*\nVWAP {c['vwap']:.2f} < 9EMA {c['9ema']:.2f} Cross | RSI {c['rsi']:.1f} ✅\n{tag}\n\n➡️ *{sym} PE @ 50-90*\n➡️ *NIFTY PE @ 50-90*"
        send_tg(msg)

if __name__=="__main__": main()
