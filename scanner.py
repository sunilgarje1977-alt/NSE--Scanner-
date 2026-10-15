import os, time, requests, json
from datetime import datetime, timedelta
from SmartApi import SmartConnect
import pandas as pd
import pyotp

API_KEY=os.getenv("ANGEL_API_KEY");CLIENT_CODE=os.getenv("ANGEL_CLIENT_ID");PASSWORD=os.getenv("ANGEL_PASSWORD");TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET");BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN");CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")

# ===== NSE 1000 FULL LIST - Large + Mid + Small =====
NSE_1000 = [
"RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","BHARTIARTL","SBIN","BAJFINANCE","ITC","LT","KOTAKBANK","MARUTI","ASIANPAINT","AXISBANK","SUNPHARMA","TITAN","ULTRACEMCO","WIPRO","NTPC","POWERGRID","ONGC","TATAMOTORS","TATASTEEL","JSWSTEEL","ADANIENT","ADANIPORTS","COALINDIA","HINDALCO","BAJAJFINSV","EICHERMOT","GRASIM","CIPLA","DIVISLAB","DRREDDY","APOLLOHOSP","BRITANNIA","NESTLEIND","BPCL","INDUSINDBK","SBILIFE","HDFCLIFE","TECHM","LTIM","HCLTECH","BAJAJ-AUTO","HEROMOTOCO","TATACONSUM","SRF","PERSISTENT","MPHASIS","COFORGE","LUPIN","AUROPHARMA","ALKEM","TORNTPHARM","ZYDUSLIFE","CUMMINSIND","ASHOKLEY","BALKRISIND","BHARATFORG","MOTHERSON","MRF","BOSCHLTD","TVSMOTOR","VOLTAS","HAVELLS","POLYCAB","KEI","DIXON","SYNGENE","LAURUSLABS","ATUL","AARTIIND","DEEPAKNTR","NAVINFLUOR","PIIND","UPL","COROMANDEL","SAIL","NMDC","VEDL","TATAPOWER","JSWENERGY","NHPC","PFC","RECLTD","IDFCFIRSTB","FEDERALBNK","BANDHANBNK","AUBANK","PNB","BANKBARODA","CDSL","BSE","MCX","ANGELONE","MUTHOOTFIN","CHOLAFIN","ZOMATO","PAYTM","NYKAA","IRCTC","INDIGO","KPITTECH","TATAELXSI","TRIDENT","BATAINDIA","IDEA","IRFC","RVNL","HAL","BEL","BHEL","SUZLON","YESBANK","ABB","ADANIGREEN","ADANIPOWER","ATGL","BANKINDIA","BERGEPAINT","BIOCON","CANBK","CHAMBLFERT","COLPAL","CONCOR","CROMPTON","CUB","DABUR","DALBHARAT","DLF","ESCORTS","EXIDEIND","GODREJPROP","GRANULES","GSPL","GUJGASLTD","HDFCAMC","ICICIGI","INDHOTEL","INDIAMART","INDIANB","INDUSTOWER","IPCALAB","JINDALSTEL","JKCEMENT","JUBLFOOD","LALPATHLAB","LICHSGFIN","M&MFIN","MANAPPURAM","MARICO","MCDOWELL-N","MFSL","MGL","NAM-INDIA","NATIONALUM","NAUKRI","OBEROIRLTY","OFSS","PAGEIND","PEL","PETRONET","PFIZER","PIDILITIND","PNB","PVRINOX","RAMCOCEM","RBLBANK","SBICARD","SHREECEM","SIEMENS","STAR","SUNTECK","TATACOMM","TRENT","UBL","UNITSPIRITS","VBL","ZEEL","AAVAS","ABFRL","AFFLE","AJANTPHARM","ALKYLAMINE","ANURAS","APLLTD","APTUS","ASTERDM","ASTRAL","BALAMINES","BAYERCROP","BDL","BEML","BSOFT","CAMPUS","CAPLIPOINT","CARBORUNUM","CENTRALBK","CESC","CHOLAHLDNG","CRAFTSMAN","CREDITACC","CYIENT","DELTACORP","DEVYANI","EASEMYTRIP","ECLERX","EIDPARRY","ELECON","ELGI","EMAMILTD","ENDURANCE","ERIS","ESABINDIA","FDC","FINEORG","FINCABLES","FLUOROCHEM","GALAXYSURF","GARFIBRES","GLAXO","GNFC","GOCOLORS","GODFRYPHLP","GRINDWELL","HAPPSTMNDS","HATSUN","HFCL","HINDCOPPER","HOMEFIRST","HONAUT","IDBI","IDFC","IEX","IIFL","INTELLECT","IRB","IRCON","JBCHEPHARM","JCHAC","JKPAPER","JUSTDIAL","JYOTHYLAB","KAJARIA","KANSAINER","KIMS","KRBL","LAOPALA","LATENTVIEW","LEMONTREE","LUXIND","MAHSEAMLES","MAPMYINDIA","MASFIN","MASTEK","MAZDOCK","MEDPLUS","METROPOLIS","MINDACORP","MIRZAINT","MMTC","MOIL","MOTILALOFS","NCC","NESCO","NH","NLCINDIA","NOCIL","NRBBEARING","OLECTRA","ORIENTELEC","PATELENG","PDSL","PGHL","PHOENIXLTD","POLYMED","POONAWALLA","PRAJIND","PRINCEPIPE","PUNJABBE","QUESS","RADICO","RAILTEL","RAJESHEXPO","RATNAMANI","RAYMOND","REDINGTON","RELAXO","RENUKA","RTNINDIA","SAPPHIRE","SCHAEFFLER","SEQUENT","SFL","SHANKARA","SJVN","SKF","SOBHA","SONACOMS","STARCEMENT","STARHEALTH","STLTECH","SUDARSCHEM","SUMICHEM","SUNDRMFAST","SUPRAJIT","SUVENPHAR","SWELECTES","SYMPHONY","TANLA","TATACOFFEE","TATAMETALI","TCI","TEAMLEASE","TECHNOE","THERMAX","TIINDIA","TIMKEN","TITAGARH","TRITURBINE","TTKPRESTIG","TTML","TV18BRDCST","UNIONBANK","VGUARD","VINATIORGA","VIPIND","VMART","VOLTAMP","WABAG","WELCORP","WELSPUNIND","WESTLIFE","WHIRLPOOL","WOCKPHARMA","ZENSARTECH"
]
NSE_150 = NSE_1000[:150]
SENT_FILE = "/tmp/sent_signals.json"

def send_tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=10)
    except: pass

def load_sent():
    try:
        if os.path.exists(SENT_FILE):
            with open(SENT_FILE,'r') as f: d=json.load(f)
            if d.get('date')!=datetime.now().strftime("%Y-%m-%d"): return {'date':datetime.now().strftime("%Y-%m-%d"),'symbols':[]}
            return d
    except: pass
    return {'date':datetime.now().strftime("%Y-%m-%d"),'symbols':[]}
def save_sent(d):
    try:
        with open(SENT_FILE,'w') as f: json.dump(d,f)
    except: pass
def get_login():
    obj=SmartConnect(api_key=API_KEY); totp=pyotp.TOTP(TOTP_SECRET).now(); obj.generateSession(CLIENT_CODE,PASSWORD,totp); return obj
def get_next_expiry():
    today=datetime.now(); days=3-today.weekday();
    if days<=0: days+=7
    return (today+timedelta(days=days)).strftime("%d%b%Y").upper()
def find_opt(obj, und, ltp, side):
    try:
        exp=get_next_expiry(); step=50 if und=="NIFTY" else 100 if ltp>2000 else 50 if ltp>500 else 10; atm=round(ltp/step)*step; best=None
        for i in range(-5,6):
            strike=atm+i*step; otype="CE" if side=="BUY" else "PE"
            try:
                res=obj.searchScrip("NFO",f"{und} {strike} {otype}")
                if res and res.get('data'):
                    token=res['data'][0]['symboltoken']; tsym=res['data'][0]['tradingsymbol']
                    ld=obj.ltpData("NFO",tsym,token)
                    if ld and ld.get('data'):
                        oltp=float(ld['data']['ltp'])/100
                        if 50<=oltp<=90: return (tsym,oltp,strike)
                        if best is None and 30<=oltp<=120: best=(tsym,oltp,strike)
            except: continue
        return best
    except: return None

def scan_stock(obj, sym):
    try:
        lr=obj.ltpData("NSE",sym,f"{sym}-EQ")
        if not lr.get('data'): return None
        ltp=float(lr['data']['ltp'])/100
        hp={"exchange":"NSE","symboltoken":lr['data'].get('symboltoken',""),"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        cd=obj.getCandleData(hp)
        if not cd.get('data'): return None
        df=pd.DataFrame(cd['data'],columns=['time','open','high','low','close','volume'])
        df['close']=df['close'].astype(float);df['open']=df['open'].astype(float);df['volume']=df['volume'].astype(int);df['high']=df['high'].astype(float);df['low']=df['low'].astype(float)
        df['typical']=(df['high']+df['low']+df['close'])/3; df['vwap']=(df['typical']*df['volume']).cumsum()/df['volume'].cumsum(); df['9ema']=df['close'].ewm(span=9).mean(); df['vol_avg']=df['volume'].rolling(20).mean()
        delta=df['close'].diff(); gain=(delta.where(delta>0,0)).rolling(14).mean(); loss=(-delta.where(delta<0,0)).rolling(14).mean(); rs=gain/loss; df['rsi']=100-(100/(1+rs))
        if len(df)<21: return None
        c=df.iloc[-1]; p=df.iloc[-2]
        buy=(c['close']>c['vwap']) and (p['vwap']<=p['9ema'] and c['vwap']>c['9ema']) and (c['close']>c['open']) and (c['volume']>c['vol_avg']*1.2) and (55<=c['rsi']<=60)
        sell=(c['close']<c['vwap']) and (p['vwap']>=p['9ema'] and c['vwap']<c['9ema']) and (c['close']<c['open']) and (c['volume']>c['vol_avg']*1.2) and (40<=c['rsi']<=45)
        if buy: return ("BUY",ltp,c)
        if sell: return ("SELL",ltp,c)
        return None
    except: return None

def main():
    sent=load_sent();
    try: obj=get_login()
    except Exception as e: send_tg(f"❌ Login Fail {e}"); return
    for sym in NSE_1000:
        if sym in sent['symbols']: continue
        res=scan_stock(obj,sym)
        if not res: continue
        side,ltp,c=res
        stock_opt=find_opt(obj,sym,ltp,side)
        try: nltp=float(obj.ltpData("NSE","NIFTY","99926000")['data']['ltp'])/100
        except: nltp=22600
        nifty_opt=find_opt(obj,"NIFTY",nltp,side)
        tag="🔵 NSE 150" if sym in NSE_150 else "🟠 Mid/Smallcap"
        s_txt=f"{stock_opt[0]} @ {stock_opt[1]:.1f}" if stock_opt else f"{sym} {('CE' if side=='BUY' else 'PE')} @ 50-90"
        n_txt=f"{nifty_opt[0]} @ {nifty_opt[1]:.1f}" if nifty_opt else f"NIFTY {('CE' if side=='BUY' else 'PE')} @ 50-90"
        if side=="BUY": msg=f"🟢 *{sym} CASH BUY @ {ltp:.2f}*\nVWAP {c['vwap']:.2f} Cross UP 9EMA | RSI {c['rsi']:.1f} ✅\n{tag}\n\n➡️ {sym} Liquid: {s_txt}\n➡️ NIFTY 50: {n_txt}\nTarget 2.5x | TSL 50%"
        else: msg=f"🔴 *{sym} CASH SELL @ {ltp:.2f}*\nVWAP {c['vwap']:.2f} Cross DOWN 9EMA | RSI {c['rsi']:.1f} ✅\n{tag}\n\n➡️ {sym} Liquid: {s_txt}\n➡️ NIFTY 50: {n_txt}\nTarget 2.5x | TSL 50%"
        send_tg(msg); sent['symbols'].append(sym); save_sent(sent); time.sleep(0.4)

if __name__=="__main__": main()
