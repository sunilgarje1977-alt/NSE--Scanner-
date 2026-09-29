# ========= V15+V17+V19 ULTIMATE FINAL - 1000 NSE + RESULT CATCH + 1:5 TRAIL =========
import os, json, time, requests, pyotp, pandas as pd
from SmartApi import SmartConnect
from datetime import datetime, timedelta

# --- CONFIG ---
API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip().replace(" ","").upper()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")

MAX_TRADES = 8
MAX_ACTIVE = 2
SL_PCT = 0.75 # Largecap 0.75% Mid 0.85% Small 1.0%

# RESULT / CORP - SKIP नाही, BONUS आहे!
RESULT_TODAY = []
CORP_ACTION_TODAY = []

ACTIVE = []
CLOSED = []
TOTAL = 0

# --- 1000 LIST (V15 वाली) ---
data = """RELIANCE TCS HDFCBANK ICICIBANK INFY ITC SBIN BHARTIARTL LT BAJFINANCE MARUTI TITAN SUNPHARMA WIPRO ULTRACEMCO NTPC POWERGRID TATAMOTORS TATASTEEL JSWSTEEL HCLTECH BAJAJFINSV ASIANPAINT ONGC ADANIENT ADANIPORTS COALINDIA GRASIM HINDALCO HINDUNILVR CIPLA DIVISLAB DRREDDY EICHERMOT BPCL BRITANNIA HEROMOTOCO ICICIPRULI SBILIFE HDFCLIFE LTIM TRENT VEDL INDUSINDBK AXISBANK KOTAKBANK BAJAJ-AUTO APOLLOHOSP TATACONSUM NESTLEIND JSWENERGY NHPC SJVN GMRINFRA IDFCFIRSTB FEDERALBNK AUBANK INDIANB BANKINDIA UNIONBANK CANBK MAHABANK PNB BANKBARODA RECLTD PFC IRFC RVNL IRCTC HAL BEL BHEL SAIL TATAPOWER ADANIGREEN ADANIPOWER IDEA YESBANK SUZLON JIOFIN ZOMATO NYKAA PAYTM POLICYBZR DELHIVERY NAUKRI INDIAMART LTF MUTHOOTFIN MANAPPURAM CHOLAFIN SHRIRAMFIN TATACHEM DEEPAKNTR AARTIIND ATUL SRF PIIND UPL COROMANDEL TORRENT POWER TORNTPHARM ALKEM AUROPHARMA LUPIN BIOCON ABB SIEMENS CUMMINSIND VOLTAS DIXON TATATECH TATAELXSI KPITTECH COFORGE PERSISTENT MPHASIS LTTS IEX MCX BSE CAMS CDSL ANGELONE ICICIGI SBICARD HUDCO IREDA IRB DLF GODREJPROP DMART POLYCAB HAVELLS INDHOTEL M&M TVSMOTOR MOTHERSON MRF MAZDOCK BDL"""
extra = """AARTIDRUGS AAVAS ABSLAMC AFFLE AIAENG AJANTPHARM AKZOINDIA ALEMBICLTD ALKYLAMINE ALOKINDS ANANDRATHI ANANTRAJ APARINDS APTUS ASAHIINDIA ASTERDM ASTRAL ATGL AVANTIFEED AWL BALAMINES BANDHANBNK BAYERCROP BBTC BLUEDART BSOFT CANFINHOME CAPLIPOINT CARBORUN CASTROLIND CCL CEATLTD CENTRALBK CERA CGCL CRAFTSMAN CREDITACC CRISIL CSBBANK CUB CYIENT DABUR DALBHARAT DCAL DCBBANK EASEMYTRIP ELGIEQUIP EMAMILTD EQUITASBNK ERIS EXIDEIND FINEORG FINCABLES FSL GALAXYSURF GESHIP GILLETTE GLAXO GLENMARK GMDCLTD GODREJCP GRANULES GRAPHITE GRINDWELL GUJALKALI GUJGASLTD HAPPSTMNDS HONASA IIFL INTELLECT IOC ISEC JBCHEPHARM JINDALSAW JUBLINGREA JUSTDIAL JYOTHYLAB KAJARIA KARURVYSYA KEC KIRLOSENG KRBL KSB KTKBANK LALPATHLAB LATENTVIEW MAPMYINDIA MARICO MASTEK MAXHEALTH MEDANTA METROPOLIS MGL NAVINFLUOR NCC NETWEB NH OFSS PATANJALI PETRONET PFIZER PIDILITIND PNCINFRA POLYMED PRAJIND PRINCEPIPE PVRINOX QUESS RADICO RAILTEL RALLIS RAMCOCEM RATNAMANI RAYMOND RBLBANK RELAXO SAPPHIRE SCHAEFFLER SEQUENT SHANKARA SHREECEM SKFINDIA SOLARINDS STAR STLTECH"""
ALL_SYMBOLS = list(dict.fromkeys((data+" "+extra).replace("\n"," ").split()))

# --- TELEGRAM ---
def tg(msg):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":msg,"parse_mode":"Markdown"})
    except: pass
    print(msg)

# --- LOGIN ---
obj = SmartConnect(api_key=API_KEY)
obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

def get_token_map():
    try:
        df=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
        m={}
        for _,r in df.iterrows():
            if r['exch_seg']=='NSE' and str(r['symbol']).endswith('-EQ'):
                s=r['symbol'].replace('-EQ','')
                if s in ALL_SYMBOLS: m[s]=str(r['token'])
        return m
    except: return {}
TOKEN_MAP=get_token_map()
print(f"Tokens {len(TOKEN_MAP)}/{len(ALL_SYMBOLS)}")

# --- INDICATORS (V15+V17) ---
def indi(df):
    c=df["close"]
    df["ema9"]=c.ewm(9).mean(); df["ema15"]=c.ewm(15).mean(); df["ema21"]=c.ewm(21).mean(); df["ema50"]=c.ewm(50).mean()
    df["vwap"]=(c*df["volume"]).cumsum()/df["volume"].cumsum()
    df["macd"]=c.ewm(12).mean()-c.ewm(26).mean(); df["macd_sig"]=df["macd"].ewm(9).mean()
    d=c.diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
    df["rsi"]=100-(100/(1+g/l)); df["vol20"]=df["volume"].rolling(20).mean()
    return df

# --- SIGNAL (V15+V17+V19 COMBINE) ---
def get_signal(df, sym, ltp, dh, dl, do, pc, news=""):
    global TOTAL, SL_PCT
    if len(ACTIVE)>=MAX_ACTIVE or TOTAL>=MAX_TRADES or len(df)<30: return None

    # V17: GAP 5%
    gap=(do-pc)/pc*100 if pc else 0
    if abs(gap)>5: return None
    # V15: LIQUIDITY
    if df["volume"].iloc[-20:].mean()<50000: return None
    # V17: NEWS NEGATIVE
    if any(k in news.lower() for k in ["fraud","scam","ban","default"]): return None

    df=indi(df); last=df.iloc[-1]
    dg=(ltp-do)/do*100 if do else 0
    m5=(df["close"].iloc[-1]-df["close"].iloc[-2])/df["close"].iloc[-2]*100
    rec=(ltp-dl)/dl*100 if dl else 0
    v20=df["volume"].iloc[-1]/df["vol20"].iloc[-1] if df["vol20"].iloc[-1]>0 else 1
    v5=df["volume"].iloc[-1]/df["volume"].iloc[-6:-1].mean() if len(df)>6 else 1

    # CAP TYPE SL (V19)
    if ltp<200: SL_PCT=1.0
    elif ltp<600: SL_PCT=0.85
    else: SL_PCT=0.75

    buy=0; sell=0; br=[]; sr=[]

    # V19: RESULT/CORP BONUS (SKIP नाही)
    if sym in RESULT_TODAY and v20>=2:
        buy+=3.0; sell+=3.0; br.append("RESULT BONUS"); sr.append("RESULT BONUS")
    if sym in CORP_ACTION_TODAY:
        buy+=1.5; sell+=1.5

    # V15: TREND
    if last["ema9"]>last["ema15"]>last["ema21"]: buy+=1.5; br.append("TREND UP")
    if last["ema9"]<last["ema15"]<last["ema21"]: sell+=1.5; sr.append("TREND DN")
    if ltp>last["ema50"]: buy+=0.5
    else: sell+=0.5

    # V15+V17: VWAP MACD RSI (तुझं 55-40)
    if ltp>last["vwap"]: buy+=1.2; br.append("VWAP+")
    else: sell+=1.2; sr.append("VWAP-")
    if last["macd"]>last["macd_sig"]: buy+=1.2; br.append("MACD+")
    else: sell+=1.2; sr.append("MACD-")
    if 55<=last["rsi"]<=70: buy+=1.0; br.append(f"RSI B {last['rsi']:.0f}")
    if 40<=last["rsi"]<=55: sell+=1.0; sr.append(f"RSI S {last['rsi']:.0f}")

    # V17: PRICE ACTION
    if dg>=0.5: buy+=1.2; br.append(f"DAY+{dg:.1f}%")
    if dg<=-0.5: sell+=1.2; sr.append(f"DAY{dg:.1f}%")
    if m5>=0.15: buy+=1.0; br.append(f"5M+{m5:.2f}%")
    if m5<=-0.15: sell+=1.0; sr.append(f"5M{m5:.2f}%")
    if ltp>=dh*0.994: buy+=1.2; br.append("NEAR HIGH")
    if rec>=1.0: buy+=1.0; br.append(f"REC {rec:.1f}%")
    if m5>=0.5 and rec>=1.0: buy+=2.5; br.append("BOUNCE POWER")

    # V17: VOLUME BLAST
    if v20>=2.5:
        if dg>0: buy+=2.5; br.append(f"VOL BLAST {v20:.1f}x")
        else: sell+=2.5; sr.append(f"VOL BLAST {v20:.1f}x")
    if v5>=2.0:
        if dg>0: buy+=1.5; br.append(f"5M VOL {v5:.1f}x")
        else: sell+=1.5; sr.append(f"5M VOL {v5:.1f}x")
    if ltp>=dh*0.992 and v5>=2.0: buy+=3.5; br.append("52W-H BLAST")
    if ltp<=dl*1.008 and v5>=2.0: sell+=3.5; sr.append("52W-L BLAST")

    if v20<0.6 and abs(dg)<0.8: return None

    side=None; score=0; reason=[]
    if buy>=3.0 and buy>sell+0.5: side="BUY"; score=buy; reason=br
    elif sell>=3.0 and sell>buy+0.5: side="SELL"; score=sell; reason=sr
    else: return None

    # V17+V19: SL = CANDLE LOW vs %
    cl=df["low"].iloc[-3:].min(); ch=df["high"].iloc[-3:].max()
    fsl_b=ltp*(1-SL_PCT/100); fsl_s=ltp*(1+SL_PCT/100)
    if side=="BUY": sl=max(cl,fsl_b); slp=(ltp-sl)/ltp*100; t1=ltp*(1+slp/100); t2=ltp*(1+slp*1.5/100)
    else: sl=min(ch,fsl_s); slp=(sl-ltp)/ltp*100; t1=ltp*(1-slp/100); t2=ltp*(1-slp*1.5/100)

    return {"symbol":sym,"side":side,"score":score,"entry":ltp,"sl":round(sl,2),"t1":round(t1,2),"t2":round(t2,2),"sl_pct":round(slp,2),"qty":100,"remain":100,"booked":0,"status":"ACTIVE","reason":" | ".join(reason)}

# --- MANAGE 50% + 1:5 TRAIL (V19) ---
def manage(mp):
    for tr in ACTIVE[:]:
        ltp=mp.get(tr["symbol"], tr["entry"])
        profit_pct=(ltp-tr["entry"])/tr["entry"]*100 if tr["side"]=="BUY" else (tr["entry"]-ltp)/tr["entry"]*100

        if tr["status"]=="ACTIVE":
            hit=(tr["side"]=="BUY" and ltp>=tr["t1"]) or (tr["side"]=="SELL" and ltp<=tr["t1"])
            if hit:
                b=tr["remain"]//2; p=(ltp-tr["entry"])*b if tr["side"]=="BUY" else (tr["entry"]-ltp)*b
                tr["remain"]-=b; tr["booked"]+=p; tr["sl"]=tr["entry"]; tr["status"]="50% TRAIL"
                tg(f"✅ 50% BOOKED {tr['symbol']} +₹{p:.0f} | SL->ENTRY")

        if tr["status"]=="50% TRAIL" and profit_pct>0:
            trail_pct=profit_pct/5 # 1:5
            new_sl=tr["entry"]*(1+trail_pct/100) if tr["side"]=="BUY" else tr["entry"]*(1-trail_pct/100)
            if (tr["side"]=="BUY" and new_sl>tr["sl"]) or (tr["side"]=="SELL" and new_sl<tr["sl"]):
                tr["sl"]=new_sl
                tg(f"🔼 TRAIL {tr['symbol']} SL {new_sl:.2f} Profit {profit_pct:.1f}% (1:5)")

        sl_hit=(tr["side"]=="BUY" and ltp<=tr["sl"]) or (tr["side"]=="SELL" and ltp>=tr["sl"])
        t2_hit=(tr["side"]=="BUY" and ltp>=tr["t2"]) or (tr["side"]=="SELL" and ltp<=tr["t2"])
        if sl_hit or t2_hit:
            pnl=(ltp-tr["entry"])*tr["remain"] if tr["side"]=="BUY" else (tr["entry"]-ltp)*tr["remain"]
            total=tr["booked"]+pnl; rs="T2" if t2_hit else "TRAIL SL" if tr["status"]!="ACTIVE" else "SL"
            CLOSED.append({"sym":tr["symbol"],"side":tr["side"],"pnl":total,"rs":rs})
            ACTIVE.remove(tr)
            tg(f"{'🟢' if total>0 else '🔴'} CLOSED {tr['symbol']} {rs} ₹{total:.0f}")

def summary():
    w=sum(1 for x in CLOSED if x["pnl"]>0); l=sum(1 for x in CLOSED if x["pnl"]<=0)
    net=sum(x["pnl"] for x in CLOSED)
    msg=f"📊 *END DAY {datetime.now().date()}* W{w} L{l} Net ₹{net:.0f} {'🟢' if net>0 else '🔴'}\nTrades {TOTAL}/8\n"
    for x in CLOSED: msg+=f"{'🟢' if x['pnl']>0 else '🔴'} {x['sym']} {x['rs']} ₹{x['pnl']:.0f}\n"
    tg(msg)

# --- SCAN ---
for sym in ALL_SYMBOLS:
    token=TOKEN_MAP.get(sym)
    if not token: continue
    try:
        params={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        c=obj.getCandleData(params)
        if not c or not c.get('data'): continue
        df=pd.DataFrame(c['data'], columns=['date','open','high','low','close','volume'])
        ltp=df["close"].iloc[-1]; dh=df["high"].iloc[-1]; dl=df["low"].iloc[-1]; do=df["open"].iloc[-1]; pc=df["close"].iloc[-2]
        sig=get_signal(df,sym,ltp,dh,dl,do,pc,"")
        if sig:
            ACTIVE.append(sig); TOTAL+=1
            tg(f"🚀 NEW {sig['side']} {sig['symbol']} @{sig['entry']} SL {sig['sl']}({sig['sl_pct']}%) T1 {sig['t1']} T2 {sig['t2']} | {sig['reason']}")
            if TOTAL>=MAX_TRADES: break
    except: continue

summary()
print("V19 DONE")
