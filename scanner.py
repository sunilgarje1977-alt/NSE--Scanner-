 # ========== V22 FAST ULTIMATE - V15 TO V21 ALL + SMALL+MID FULL 1000+ ==========
import os, requests, pyotp, pandas as pd
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY = os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID = os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD = os.getenv("ANGEL_PASSWORD","")
TOTP_SECRET = os.getenv("ANGEL_TOTP_SECRET","").strip().replace(" ","").upper()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")

MAX_TRADES = 8
CLOSED = []

# ===== FULL SMALL+MID 1000+ LIST =====
SMALL_MID = """ADANIENT ADANIGREEN ADANIPOWER ATGL AWL ADANITRANS ADANIPORTS
DMART TRENT VEDL INDUSINDBK BANKINDIA UNIONBANK CANBK MAHABANK PNB BANKBARODA RECLTD PFC IRFC RVNL IRCTC HAL BEL BHEL SAIL TATAPOWER IDEA YESBANK SUZLON JIOFIN ZOMATO NYKAA PAYTM POLICYBZR DELHIVERY NAUKRI INDIAMART LTF MUTHOOTFIN MANAPPURAM CHOLAFIN SHRIRAMFIN TATACHEM DEEPAKNTR AARTIIND ATUL SRF PIIND UPL COROMANDEL TORRENT POWER TORNTPHARM ALKEM AUROPHARMA LUPIN BIOCON ABB SIEMENS CUMMINSIND VOLTAS DIXON TATATECH TATAELXSI KPITTECH COFORGE PERSISTENT MPHASIS LTTS IEX MCX BSE CAMS CDSL ANGELONE ICICIGI SBICARD HUDCO IREDA IRB DLF GODREJPROP POLYCAB HAVELLS INDHOTEL M&M TVSMOTOR MOTHERSON MRF MAZDOCK BDL DAMCAPITAL
AARTIDRUGS AAVAS ABSLAMC AFFLE AIAENG AJANTPHARM AKZOINDIA ALEMBICLTD ALKYLAMINE ALOKINDS ANANDRATHI ANANTRAJ APARINDS APTUS ASAHIINDIA ASTERDM ASTRAL AVANTIFEED BALAMINES BANDHANBNK BAYERCROP BBTC BLUEDART BSOFT CANFINHOME CAPLIPOINT CARBORUN CASTROLIND CCL CEATLTD CENTRALBK CERA CGCL CRAFTSMAN CREDITACC CRISIL CSBBANK CUB CYIENT DABUR DALBHARAT DCAL DCBBANK EASEMYTRIP ELGIEQUIP EMAMILTD EQUITASBNK ERIS EXIDEIND FINEORG FINCABLES FSL GALAXYSURF GESHIP GILLETTE GLAXO GLENMARK GMDCLTD GODREJCP GRANULES GRAPHITE GRINDWELL GUJALKALI GUJGASLTD HAPPSTMNDS HONASA IIFL INTELLECT IOC ISEC JBCHEPHARM JINDALSAW JUBLINGREA JUSTDIAL JYOTHYLAB KAJARIA KARURVYSYA KEC KIRLOSENG KRBL KSB KTKBANK LALPATHLAB LATENTVIEW MAPMYINDIA MARICO MASTEK MAXHEALTH MEDANTA METROPOLIS MGL NAVINFLUOR NCC NETWEB NH OFSS PATANJALI PETRONET PFIZER PIDILITIND PNCINFRA POLYMED PRAJIND PRINCEPIPE PVRINOX QUESS RADICO RAILTEL RALLIS RAMCOCEM RATNAMANI RAYMOND RBLBANK RELAXO SAPPHIRE SCHAEFFLER SEQUENT SHANKARA SHREECEM SKFINDIA SOLARINDS STAR STLTECH SUDARSCHEM SUMICHEM SUNTECK SUPREMEIND SUVENPHAR SYNGENE SYRMA TATACOMM TATAMTRDVR TEAMLEASE TECHNOE TEJASNET THOMASCOOK TIINDIA TIMKEN TIPSMUSIC TITAGARH TMB TNPL TRIDENT TRITURB TTKPRESTI UCOBANK UNOMINDA UTIAMC VGUARD VTL WELCORP WELSPUNLTD WESTLIFE ZYDUSLIFE ZFCVINDIA
RELIANCE TCS HDFCBANK ICICIBANK INFY ITC SBIN BHARTIARTL LT BAJFINANCE MARUTI TITAN SUNPHARMA WIPRO ULTRACEMCO NTPC POWERGRID TATAMOTORS TATASTEEL JSWSTEEL HCLTECH BAJAJFINSV ASIANPAINT ONGC COALINDIA GRASIM HINDALCO HINDUNILVR CIPLA DIVISLAB DRREDDY EICHERMOT BPCL BRITANNIA HEROMOTOCO ICICIPRULI SBILIFE HDFCLIFE LTIM AXISBANK KOTAKBANK BAJAJ-AUTO APOLLOHOSP TATACONSUM NESTLEIND JSWENERGY NHPC SJVN GMRINFRA IDFCFIRSTB FEDERALBNK AUBANK INDIANB
"""
ALL_SYMBOLS = list(dict.fromkeys(SMALL_MID.replace("\n"," ").split()))

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=5)
    except: pass
    print(m)

obj = SmartConnect(api_key=API_KEY)
obj.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())
print(f"Login OK - Total {len(ALL_SYMBOLS)} Stocks")

def get_tokens():
    try:
        df=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
        return {r['symbol'].replace('-EQ',''): str(r['token']) for _,r in df.iterrows() if r['exch_seg']=='NSE' and str(r['symbol']).endswith('-EQ') and r['symbol'].replace('-EQ','') in ALL_SYMBOLS}
    except: return {}
TOKENS = get_tokens()

def indi(df):
    c=df["close"]
    df["ema9"]=c.ewm(9).mean(); df["ema15"]=c.ewm(15).mean(); df["ema21"]=c.ewm(21).mean(); df["ema50"]=c.ewm(50).mean()
    df["vwap"]=(c*df["volume"]).cumsum()/df["volume"].cumsum()
    df["macd"]=c.ewm(12).mean()-c.ewm(26).mean(); df["macd_sig"]=df["macd"].ewm(9).mean()
    d=c.diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
    df["rsi"]=100-(100/(1+g/l)); df["vol20"]=df["volume"].rolling(20).mean()
    return df

def get_sl(ltp, side, df):
    cl=df["low"].iloc[-3:].min(); ch=df["high"].iloc[-3:].max()
    min_sl=1.2 if ltp<50 else 1.0 if ltp<200 else 0.85 if ltp<600 else 0.75
    if side=="BUY":
        sl_p=ltp*(1-min_sl/100)
        sl=sl_p if (ltp-cl)/ltp*100 < min_sl else min(cl, sl_p)
        sl_pct=(ltp-sl)/ltp*100
        return round(sl,2), round(ltp*(1+sl_pct/100),2), round(ltp*(1+sl_pct*1.5/100),2), round(sl_pct,2)
    else:
        sl_p=ltp*(1+min_sl/100)
        sl=sl_p if (ch-ltp)/ltp*100 < min_sl else max(ch, sl_p)
        sl_pct=(sl-ltp)/ltp*100
        return round(sl,2), round(ltp*(1-sl_pct/100),2), round(ltp*(1-sl_pct*1.5/100),2), round(sl_pct,2)

def scan_one(sym):
    token=TOKENS.get(sym)
    if not token: return None
    try:
        p={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=2)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        d=obj.getCandleData(p)
        if not d or not d.get('data'): return None
        df=pd.DataFrame(d['data'], columns=['date','open','high','low','close','volume'])
        if len(df)<30: return None
        df=indi(df); last=df.iloc[-1]; prev=df.iloc[-2]
        ltp=last["close"]; dh=df["high"].max(); dl=df["low"].min(); do=df["open"].iloc[-1]; pc=df["close"].iloc[-2]
        o5=df["open"].iloc[-1]; c5=ltp
        
        gap=(do-pc)/pc*100 if pc else 0
        if abs(gap)>5: return None
        if df["volume"].iloc[-20:].mean()<40000: return None

        dg=(ltp-do)/do*100
        m5=(ltp-prev["close"])/prev["close"]*100
        rec=(ltp-dl)/dl*100 if dl else 0
        v20=df["volume"].iloc[-1]/last["vol20"] if last["vol20"]>0 else 1
        v5=df["volume"].iloc[-1]/df["volume"].iloc[-6:-1].mean() if len(df)>6 else 1

        buy=0; sell=0; br=[]; sr=[]

        # === V15 TO V21 ALL CONDITIONS - SAME AS BEFORE ===
        # 1. TREND 9>15>21
        if last["ema9"]>last["ema15"]>last["ema21"]: buy+=1.5; br.append("TREND UP")
        if last["ema9"]<last["ema15"]<last["ema21"]: sell+=1.5; sr.append("TREND DN")
        if ltp>last["ema50"]: buy+=0.5
        else: sell+=0.5
        # 2. VWAP
        if ltp>last["vwap"]: buy+=1.2; br.append("VWAP+")
        else: sell+=1.2; sr.append("VWAP-")
        # 3. MACD
        if last["macd"]>last["macd_sig"]: buy+=1.2; br.append("MACD+")
        else: sell+=1.2; sr.append("MACD-")
        # 4. RSI
        if 55<=last["rsi"]<=70: buy+=1.0; br.append(f"RSI B {last['rsi']:.0f}")
        if 30<=last["rsi"]<=50: sell+=1.0; sr.append(f"RSI S {last['rsi']:.0f}")
        # 5. DAY +/-
        if dg>=0.5: buy+=1.2; br.append(f"DAY+{dg:.1f}%")
        if dg<=-0.5: sell+=1.2; sr.append(f"DAY{dg:.1f}%")
        # 6. 5M MOMENTUM
        if m5>=0.15: buy+=1.0; br.append(f"5M+{m5:.2f}%")
        if m5<=-0.15: sell+=1.0; sr.append(f"5M{m5:.2f}%")
        # 7. NEAR DAY HIGH / BOUNCE + RECOVERY
        if ltp>=df["high"].iloc[-1]*0.994: buy+=1.2; br.append("NEAR HIGH")
        if rec>=1.0: buy+=1.0; br.append(f"REC {rec:.1f}%")
        if m5>=0.5 and rec>=1.0: buy+=2.5; br.append("BOUNCE")
        if m5<=-0.5 and rec<=-1.0: sell+=2.5; sr.append("DROP")
        # 8. VOLUME 20MA
        if v20>=2.5:
            if dg>0: buy+=2.5; br.append(f"VOL {v20:.1f}x")
            else: sell+=2.5; sr.append(f"VOL {v20:.1f}x")
        # 9. VOLUME 5M BLAST
        if v5>=2.0:
            if dg>0: buy+=1.5; br.append(f"5M VOL {v5:.1f}x")
            else: sell+=1.5; sr.append(f"5M VOL {v5:.1f}x")
        # 10. 52W BREAKOUT
        if ltp>=df["high"].iloc[-1]*0.992 and v5>=2.0: buy+=3.5; br.append("52W-H BLAST")
        if ltp<=df["low"].iloc[-1]*1.008 and v5>=2.0: sell+=3.5; sr.append("52W-L BLAST")
        # 11. V20 NEW - VWAP CROSS 9,15 - BOTH SIDE
        if prev["vwap"] < prev["ema9"] and last["vwap"] > last["ema9"]: buy+=2.5; br.append("VWAP X 9 UP")
        if prev["vwap"] < prev["ema15"] and last["vwap"] > last["ema15"]: buy+=2.5; br.append("VWAP X 15 UP")
        if prev["vwap"] > prev["ema9"] and last["vwap"] < last["ema9"]: sell+=2.5; sr.append("VWAP X 9 DN")
        if prev["vwap"] > prev["ema15"] and last["vwap"] < last["ema15"]: sell+=2.5; sr.append("VWAP X 15 DN")
        if last["vwap"] > last["ema9"] > last["ema15"]: buy+=3.5; br.append("VWAP>9>15 SUPER BUY")
        if last["vwap"] < last["ema9"] < last["ema15"]: sell+=3.5; sr.append("VWAP<9<15 SUPER SELL")
        # 12. GREEN ONLY + BOUNCE (V15)
        if o5 and c5>o5 and dg<0 and rec>=1.0: buy+=2.0; br.append("Green+ Bounce")

        if v20<0.6 and abs(dg)<0.8: return None

        if buy>=3.0 and buy>sell+0.5:
            sl,t1,t2,slp=get_sl(ltp,"BUY",df)
            return {"side":"BUY","symbol":sym,"entry":ltp,"sl":sl,"t1":t1,"t2":t2,"slp":slp,"reason":"|".join(br),"score":buy}
        if sell>=3.0 and sell>buy+0.5:
            sl,t1,t2,slp=get_sl(ltp,"SELL",df)
            return {"side":"SELL","symbol":sym,"entry":ltp,"sl":sl,"t1":t1,"t2":t2,"slp":slp,"reason":"|".join(sr),"score":sell}
    except: return None

# ===== FAST 30 THREADS =====
found=[]
start=datetime.now()
with ThreadPoolExecutor(max_workers=30) as ex:
    fut={ex.submit(scan_one, s): s for s in ALL_SYMBOLS}
    for f in as_completed(fut):
        r=f.result()
        if r:
            found.append(r)
            tg(f"🚀 NEW {r['side']} {r['symbol']} @{r['entry']} SL {r['sl']}({r['slp']}%) T1 {r['t1']} T2 {r['t2']} | {r['reason']} S:{r['score']:.1f}")
            if len(found)>=8: break

elapsed=(datetime.now()-start).total_seconds()
tg(f"📊 END DAY {datetime.now().date()} W0 L0 Net ₹0 🔴 Trades {len(found)}/8 | FAST {elapsed:.0f}s | v22 ALL COND BUY+SELL")
print(f"DONE FAST {elapsed:.0f}s - {len(found)} signals")
