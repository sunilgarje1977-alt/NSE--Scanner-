import os, requests
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
import pyotp
from concurrent.futures import ThreadPoolExecutor, as_completed

# ENV
API_KEY=os.getenv("ANGEL_API_KEY")
CLIENT_CODE=os.getenv("ANGEL_CLIENT_ID")
PASSWORD=os.getenv("ANGEL_PASSWORD")
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET")
BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")

# NSE 200 Valid List - NSE 150 + Midcap
NSE_200 = ["RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","ASIANPAINT","AXISBANK","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","BAJAJFINSV","EICHERMOT","GRASIM","CIPLA","DIVISLAB","DRREDDY","APOLLOHOSP","BRITANNIA","NESTLEIND","BPCL","INDUSINDBK","SBILIFE","HDFCLIFE","TECHM","LTIM","HCLTECH","BAJAJ-AUTO","HEROMOTOCO","TATACONSUM","SRF","PERSISTENT","MPHASIS","COFORGE","LUPIN","AUROPHARMA","ALKEM","TORNTPHARM","ZYDUSLIFE","CUMMINSIND","ASHOKLEY","BALKRISIND","BHARATFORG","MOTHERSON","MRF","BOSCHLTD","TVSMOTOR","VOLTAS","HAVELLS","POLYCAB","KEI","DIXON","SYNGENE","LAURUSLABS","ATUL","AARTIIND","DEEPAKNTR","NAVINFLUOR","PIIND","UPL","COROMANDEL","SAIL","NMDC","VEDL","TATAPOWER","JSWENERGY","NHPC","PFC","RECLTD","IDFCFIRSTB","FEDERALBNK","BANDHANBNK","AUBANK","PNB","BANKBARODA","CDSL","BSE","MCX","ANGELONE","MUTHOOTFIN","CHOLAFIN","ZOMATO","PAYTM","NYKAA","IRCTC","INDIGO","KPITTECH","TATAELXSI","TRIDENT","BATAINDIA","IDEA","IRFC","RVNL","HAL","BEL","BHEL","SUZLON","YESBANK","SULA","TATACHEM","ABCAPITAL","ABFRL","ADANIGREEN","ADANIPOWER","ATGL","BANKINDIA","BERGEPAINT","BIOCON","CANBK","CHAMBLFERT","COLPAL","CONCOR","CROMPTON","CUB","DABUR","DALBHARAT","DLF","ESCORTS","EXIDEIND","GODREJPROP","GRANULES","GSPL","GUJGASLTD","HDFCAMC","ICICIGI","INDHOTEL","INDIAMART","INDIANB","INDUSTOWER","IPCALAB","JINDALSTEL","JKCEMENT","JUBLFOOD","LALPATHLAB","LICHSGFIN","M&MFIN","MANAPPURAM","MARICO","MCDOWELL-N","MFSL","MGL","NAM-INDIA","NATIONALUM","NAUKRI","OBEROIRLTY","OFSS","PAGEIND","PEL","PETRONET","PFIZER","PIDILITIND","PVRINOX","RAMCOCEM","RBLBANK","SBICARD","SHREECEM","SIEMENS","STAR","SUNTECK","TATACOMM","TRENT","UBL","UNITSPIRITS","VBL","ZEEL"]

NSE_150 = NSE_200[:150]

def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=15)
    except: pass

def get_login():
    obj=SmartConnect(api_key=API_KEY)
    totp=pyotp.TOTP(TOTP_SECRET).now()
    obj.generateSession(CLIENT_CODE,PASSWORD,totp)
    return obj

def get_option_premium(obj, stock, underlying_ltp, opt_type):
    """NSE 150 मधून 50-90 Premium असलेला Option शोधणे"""
    try:
        atm = round(underlying_ltp / 50) * 50 if underlying_ltp > 500 else round(underlying_ltp / 10) * 10
        strikes = [atm, atm+50, atm+100, atm-50] if opt_type=="CE" else [atm, atm-50, atm-100, atm+50]
        res = obj.searchScrip("NFO", stock)
        if not res.get('data'): return None
        for strike in strikes:
            for item in res['data']:
                try:
                    if str(strike) in item['tradingsymbol'] and opt_type in item['tradingsymbol'] and stock in item['tradingsymbol']:
                        lr = obj.ltpData("NFO", item['tradingsymbol'], item['symboltoken'])
                        if lr.get('data'):
                            ltp = float(lr['data']['ltp'])
                            if ltp>1000: ltp/=100
                            if 50 <= ltp <= 90:
                                return item['tradingsymbol'], ltp
                except: continue
        return None
    except: return None

def scan_one(args):
    obj, sym = args
    try:
        lr=obj.ltpData("NSE", sym, f"{sym}-EQ")
        if not lr.get('data'): return None
        ltp=float(lr['data']['ltp'])
        if ltp>10000: ltp/=100
        token=lr['data']['symboltoken']

        today=datetime.now().strftime("%Y-%m-%d")
        hp={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today} 09:15","todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        cd=obj.getCandleData(hp)
        if not cd.get('data') or len(cd['data'])<15: return None

        df=pd.DataFrame(cd['data'], columns=['time','open','high','low','close','volume'])
        for col in ['close','open','high','low','volume']: df[col]=pd.to_numeric(df[col])

        # VWAP
        df['typical']=(df['high']+df['low']+df['close'])/3
        df['vwap']=(df['typical']*df['volume']).cumsum()/df['volume'].cumsum()
        # 9EMA
        df['9ema']=df['close'].ewm(span=9).mean()
        # Vol Avg
        df['vol_avg']=df['volume'].rolling(10).mean()
        # RSI
        delta=df['close'].diff()
        gain=(delta.where(delta>0,0)).rolling(14).mean()
        loss=(-delta.where(delta<0,0)).rolling(14).mean()
        rs=gain/loss
        df['rsi']=100-(100/(1+rs))

        c=df.iloc[-1]
        p=df.iloc[-2]

        # ===== SCREENSHOT LOGIC - EXACT 5 CONDITIONS =====
        cross_up = (p['vwap'] <= p['9ema'] and c['vwap'] > c['9ema'])
        cross_down = (p['vwap'] >= p['9ema'] and c['vwap'] < c['9ema'])

        # BUY: Price>VWAP + Cross UP + Green + Vol 1.2x + RSI 55-60
        buy = (c['close'] > c['vwap']) and cross_up and (c['close'] > c['open']) and (c['volume'] > c['vol_avg']*1.2) and (55 <= c['rsi'] <= 60)

        # SELL: Price<VWAP + Cross DOWN + Red + Vol 1.2x + RSI 40-45
        sell = (c['close'] < c['vwap']) and cross_down and (c['close'] < c['open']) and (c['volume'] > c['vol_avg']*1.2) and (40 <= c['rsi'] <= 45)

        if buy: return ("BUY",sym,ltp,c)
        if sell: return ("SELL",sym,ltp,c)
        return None
    except: return None

def main():
    try: obj=get_login()
    except Exception as e:
        send_tg(f"❌ Login Fail {e}")
        return

    results=[]
    with ThreadPoolExecutor(max_workers=15) as ex:
        futs=[ex.submit(scan_one,(obj,s)) for s in NSE_200]
        for f in as_completed(futs):
            r=f.result()
            if r: results.append(r)

    if len(results)==0:
        send_tg(f"ℹ️ No Signal @ {datetime.now().strftime('%H:%M:%S')}\nChecked {len(NSE_200)} | Logic: Price>VWAP + VWAP Cross UP 9EMA + Green + Vol 1.2x + RSI 55-60")
        return

    for side,sym,ltp,c in results[:8]:
        opt_type = "CE" if side=="BUY" else "PE"
        opt = get_option_premium(obj, sym, ltp, opt_type) if sym in NSE_150 else None

        if opt:
            opt_line = f"• NSE 150 Liquid {opt[0]} @ {opt[1]:.1f} (50-90) ✅"
        else:
            opt_line = f"• NSE 150 Liquid {sym} {opt_type} @ 50-90"

        mid_line = f"• Mid/Smallcap Liquid {sym} {opt_type} @ 50-90" if sym not in NSE_150 else f"• Mid/Smallcap Liquid {opt_type} @ 50-90"

        if side=="BUY":
            msg=(f"🟢 *{sym} CASH BUY @ {ltp:.2f}*\n"
                 f"Price {ltp:.2f} > VWAP {c['vwap']:.2f}\nVWAP Cross UP 9EMA {c['9ema']:.2f}\nGreen + Vol {c['volume']/c['vol_avg']:.1f}x + RSI {c['rsi']:.1f}\n\n"
                 f"*4 Level Option Logic:*\n• NSE Cash Share BUY\n{opt_line}\n{mid_line}\n• Nifty 50 {opt_type} @ 50-90")
        else:
            msg=(f"🔴 *{sym} CASH SELL @ {ltp:.2f}*\n"
                 f"Price {ltp:.2f} < VWAP {c['vwap']:.2f}\nVWAP Cross DOWN 9EMA\nRSI {c['rsi']:.1f}\n\n"
                 f"*4 Level Option Logic:*\n• NSE Cash Share SELL\n{opt_line}\n{mid_line}\n• Nifty 50 {opt_type} @ 50-90")
        send_tg(msg)

if __name__=="__main__":
    main()
