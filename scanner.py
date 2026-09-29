import os, requests, pyotp, pandas as pd, time
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

API_KEY=os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD=os.getenv("ANGEL_PASSWORD","")
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET","").strip().replace(" ","").upper()
BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","")

MAX_TRADES=8; MAX_ACTIVE=2; ACTIVE=[]; CLOSED=[]; TOTAL=0
ALL_SYMBOLS="""RELIANCE TCS HDFCBANK ICICIBANK INFY ITC SBIN BHARTIARTL LT BAJFINANCE MARUTI TITAN SUNPHARMA WIPRO ULTRACEMCO NTPC POWERGRID TATAMOTORS TATASTEEL JSWSTEEL HCLTECH BAJAJFINSV ASIANPAINT ONGC ADANIENT ADANIPORTS COALINDIA GRASIM HINDALCO HINDUNILVR CIPLA DIVISLAB DRREDDY EICHERMOT BPCL BRITANNIA HEROMOTOCO ICICIPRULI SBILIFE HDFCLIFE LTIM TRENT VEDL INDUSINDBK AXISBANK KOTAKBANK BAJAJ-AUTO APOLLOHOSP TATACONSUM NESTLEIND JSWENERGY NHPC SJVN GMRINFRA IDFCFIRSTB FEDERALBNK AUBANK INDIANB BANKINDIA UNIONBANK CANBK MAHABANK PNB BANKBARODA RECLTD PFC IRFC RVNL IRCTC HAL BEL BHEL SAIL TATAPOWER ADANIGREEN ADANIPOWER IDEA YESBANK SUZLON JIOFIN ZOMATO NYKAA PAYTM POLICYBZR DELHIVERY NAUKRI INDIAMART LTF MUTHOOTFIN MANAPPURAM CHOLAFIN SHRIRAMFIN TATACHEM DEEPAKNTR AARTIIND ATUL SRF PIIND UPL COROMANDEL ABB SIEMENS VOLTAS DIXON TATATECH TATAELXSI KPITTECH COFORGE PERSISTENT MPHASIS LTTS IEX MCX BSE CAMS CDSL ANGELONE DLF GODREJPROP DMART POLYCAB HAVELLS INDHOTEL M&M TVSMOTOR MOTHERSON MRF MAZDOCK BDL DAMCAPITAL HUDCO ALOKINDS CENTRALBK""".split()
RESULT_TODAY=["HUDCO","RECLTD","DAMCAPITAL","MAZDOCK","ALOKINDS"]

def tg(m):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"},timeout=5)
    except: pass
    print(m,flush=True)

obj=SmartConnect(api_key=API_KEY)
obj.generateSession(CLIENT_ID,PASSWORD,pyotp.TOTP(TOTP_SECRET).now())
tg(f"🚀 V23 START {datetime.now().strftime('%H:%M')} | {len(ALL_SYMBOLS)} Stocks")

def get_tokens():
    try:
        df=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
        return {r['symbol'].replace('-EQ',''):str(r['token']) for _,r in df.iterrows() if r['exch_seg']=='NSE' and str(r['symbol']).endswith('-EQ') and r['symbol'].replace('-EQ','') in ALL_SYMBOLS}
    except: return {}
TOKENS=get_tokens()

def indi(df):
    c=df["close"]; df["ema9"]=c.ewm(9).mean(); df["ema15"]=c.ewm(15).mean(); df["ema21"]=c.ewm(21).mean(); df["ema50"]=c.ewm(50).mean()
    df["vwap"]=(c*df["volume"]).cumsum()/df["volume"].cumsum()
    df["macd"]=c.ewm(12).mean()-c.ewm(26).mean(); df["macd_sig"]=df["macd"].ewm(9).mean()
    d=c.diff(); g=d.where(d>0,0).rolling(14).mean(); l=-d.where(d<0,0).rolling(14).mean()
    df["rsi"]=100-(100/(1+g/l)); df["vol20"]=df["volume"].rolling(20).mean()
    return df

def get_sl(ltp,side,df):
    cl=df["low"].iloc[-3:].min(); ch=df["high"].iloc[-3:].max()
    min_sl=1.2 if ltp<50 else 1.0 if ltp<200 else 0.85 if ltp<600 else 0.75
    if side=="BUY":
        sl_p=ltp*(1-min_sl/100); sl=sl_p if (ltp-cl)/ltp*100<min_sl else min(cl,sl_p); sl_pct=(ltp-sl)/ltp*100
        return round(sl,2),round(ltp*(1+sl_pct/100),2),round(ltp*(1+sl_pct*1.5/100),2),round(sl_pct,2)
    else:
        sl_p=ltp*(1+min_sl/100); sl=sl_p if (ch-ltp)/ltp*100<min_sl else max(ch,sl_p); sl_pct=(sl-ltp)/ltp*100
        return round(sl,2),round(ltp*(1-sl_pct/100),2),round(ltp*(1-sl_pct*1.5/100),2),round(sl_pct,2)

def scan_one(sym):
    if sym in [a["symbol"] for a in ACTIVE]: return None
    token=TOKENS.get(sym)
    if not token: return None
    try:
        p={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=5)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
        d=obj.getCandleData(p)
        if not d or not d.get('data'): return None
        df=pd.DataFrame(d['data'],columns=['date','open','high','low','close','volume'])
        if len(df)<30: return None
        df=indi(df); last=df.iloc[-1]; prev=df.iloc[-2]
        ltp=last["close"]; do=df["open"].iloc[-1]; pc=df["close"].iloc[-2]; dh=df["high"].iloc[-1]; dl=df["low"].iloc[-1]
        dg=(ltp-do)/do*100; gap=(do-pc)/pc*100 if pc else 0; m5=(ltp-prev["close"])/prev["close"]*100; rec=(ltp-dl)/dl*100
        v20=df["volume"].iloc[-1]/last["vol20"] if last["vol20"]>0 else 1; v5=df["volume"].iloc[-1]/df["volume"].iloc[-6:-1].mean() if len(df)>6 else 1
        high_52=df["high"].max(); near_52h=(ltp/high_52)*100; low_52=df["low"].min(); near_52l=(ltp/low_52)*100
        if abs(gap)>5 or df["volume"].iloc[-20:].mean()<40000: return None
        buy=0; sell=0; br=[]; sr=[]
        if last["ema9"]>last["ema15"]>last["ema21"]: buy+=1.5; br.append("TREND UP")
        if last["ema9"]<last["ema15"]<last["ema21"]: sell+=1.5; sr.append("TREND DN")
        if ltp>last["ema50"]: buy+=0.5
        else: sell+=0.5
        if ltp>last["vwap"]: buy+=1.2; br.append("VWAP+")
        else: sell+=1.2; sr.append("VWAP-")
        if last["macd"]>last["macd_sig"]: buy+=1.2; br.append("MACD+")
        else: sell+=1.2; sr.append("MACD-")
        if 55<=last["rsi"]<=70: buy+=1.0; br.append(f"RSI B {last['rsi']:.0f}")
        if 30<=last["rsi"]<=50: sell+=1.0; sr.append(f"RSI S {last['rsi']:.0f}")
        if dg>=0.5: buy+=1.2; br.append(f"DAY+{dg:.1f}%")
        if dg<=-0.5: sell+=1.2; sr.append(f"DAY{dg:.1f}%")
        if m5>=0.15: buy+=1.0; br.append(f"5M+{m5:.2f}%")
        if m5<=-0.15: sell+=1.0; sr.append(f"5M{m5:.2f}%")
        if ltp>=dh*0.994: buy+=1.2; br.append("NEAR HIGH")
        if rec>=1.0: buy+=1.0; br.append(f"REC {rec:.1f}%")
        if m5>=0.5 and rec>=1.0: buy+=2.5; br.append("BOUNCE")
        if m5<=-0.5 and rec<=-1.0: sell+=2.5; sr.append("DROP")
        if df["open"].iloc[-1]<ltp and dg<0 and rec>=1.0: buy+=2.0; br.append("Green Bounce")
        if sym in RESULT_TODAY and v20>=2.0: buy+=3.0; sell+=3.0; br.append("RESULT BONUS"); sr.append("RESULT BONUS")
        if sym in RESULT_TODAY and v5>=2.5: buy+=4.0; sell+=4.0; br.append("RESULT+VOL BLAST")
        if v20>=2.5:
            if dg>0: buy+=2.5; br.append(f"VOL {v20:.1f}x")
            else: sell+=2.5; sr.append(f"VOL {v20:.1f}x")
        if v5>=2.0:
            if dg>0: buy+=1.5; br.append(f"5M VOL {v5:.1f}x")
            else: sell+=1.5; sr.append(f"5M VOL {v5:.1f}x")
        if ltp>=dh*0.992 and v5>=2.0: buy+=3.5; br.append("DAY-H BLAST")
        if ltp<=dl*1.008 and v5>=2.0: sell+=3.5; sr.append("DAY-L BLAST")
        if prev["vwap"]<prev["ema9"] and last["vwap"]>last["ema9"]: buy+=2.5; br.append("VWAP X 9 UP")
        if prev["vwap"]<prev["ema15"] and last["vwap"]>last["ema15"]: buy+=2.5; br.append("VWAP X 15 UP")
        if prev["vwap"]>prev["ema9"] and last["vwap"]<last["ema9"]: sell+=2.5; sr.append("VWAP X 9 DN")
        if prev["vwap"]>prev["ema15"] and last["vwap"]<last["ema15"]: sell+=2.5; sr.append("VWAP X 15 DN")
        if last["vwap"]>last["ema9"]>last["ema15"]: buy+=3.5; br.append("VWAP>9>15 SUPER BUY")
        if last["vwap"]<last["ema9"]<last["ema15"]: sell+=3.5; sr.append("VWAP<9<15 SUPER SELL")
        if near_52h>=98: buy+=4.0; br.append(f"52W-H {near_52h:.1f}%")
        if near_52l<=102: sell+=4.0; sr.append(f"52W-L {near_52l:.1f}%")
        if dg>=2.0 and v20>=2.5: buy+=2.5; br.append(f"TOP GAINER {dg:.1f}%")
        if dg<=-2.0 and v20>=2.5: sell+=2.5; sr.append(f"TOP LOSER {dg:.1f}%")
        if near_52h>=98 and v20>=3 and dg>=2: buy+=5.0; br.append("JACKPOT 🚀")
        if near_52l<=102 and v20>=3 and dg<=-2: sell+=5.0; sr.append("JACKPOT 💥")
        if v20<0.6 and abs(dg)<0.8: return None
        if buy>=3.0 and buy>sell+0.5:
            sl,t1,t2,slp=get_sl(ltp,"BUY",df)
            return {"side":"BUY","symbol":sym,"entry":ltp,"sl":sl,"t1":t1,"t2":t2,"slp":slp,"reason":"|".join(br),"score":buy,"status":"ACTIVE"}
        if sell>=3.0 and sell>buy+0.5:
            sl,t1,t2,slp=get_sl(ltp,"SELL",df)
            return {"side":"SELL","symbol":sym,"entry":ltp,"sl":sl,"t1":t1,"t2":t2,"slp":slp,"reason":"|".join(sr),"score":sell,"status":"ACTIVE"}
    except: return None

while True:
    try:
        for tr in ACTIVE[:]:
            try:
                token=TOKENS.get(tr["symbol"])
                p={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")}
                d=obj.getCandleData(p)
                if not d or not d.get('data'): continue
                ltp=pd.DataFrame(d['data'],columns=['date','open','high','low','close','volume'])["close"].iloc[-1]
                profit_pct=(ltp-tr["entry"])/tr["entry"]*100 if tr["side"]=="BUY" else (tr["entry"]-ltp)/tr["entry"]*100
                if tr["status"]=="ACTIVE" and ((tr["side"]=="BUY" and ltp>=tr["t1"]) or (tr["side"]=="SELL" and ltp<=tr["t1"])):
                    tr["status"]="50% TRAIL"; tr["sl"]=tr["entry"]
                    tg(f"✅ 50% BOOKED {tr['symbol']} T1 | SL->ENTRY | {profit_pct:.1f}%")
                if tr["status"]=="50% TRAIL" and profit_pct>0:
                    trail=profit_pct/5; new_sl=tr["entry"]*(1+trail/100) if tr["side"]=="BUY" else tr["entry"]*(1-trail/100)
                    if (tr["side"]=="BUY" and new_sl>tr["sl"]) or (tr["side"]=="SELL" and new_sl<tr["sl"]):
                        tr["sl"]=new_sl; tg(f"🔼 TRAIL {tr['symbol']} SL {new_sl:.2f} | {profit_pct:.1f}%")
                sl_hit=(tr["side"]=="BUY" and ltp<=tr["sl"]) or (tr["side"]=="SELL" and ltp>=tr["sl"])
                t2_hit=(tr["side"]=="BUY" and ltp>=tr["t2"]) or (tr["side"]=="SELL" and ltp<=tr["t2"])
                if sl_hit or t2_hit:
                    pnl=(ltp-tr["entry"])*100 if tr["side"]=="BUY" else (tr["entry"]-ltp)*100
                    CLOSED.append(tr); ACTIVE.remove(tr)
                    tg(f"{'🟢' if pnl>0 else '🔴'} CLOSED {tr['symbol']} {'T2' if t2_hit else 'SL'} ₹{pnl:.0f} | ACTIVE {len(ACTIVE)}/{MAX_ACTIVE} | TOTAL {TOTAL}/{MAX_TRADES}")
            except: continue
        if len(ACTIVE)<MAX_ACTIVE and TOTAL<MAX_TRADES:
            with ThreadPoolExecutor(max_workers=30) as ex:
                fut={ex.submit(scan_one,s):s for s in ALL_SYMBOLS}
                for f in as_completed(fut):
                    r=f.result()
                    if r and len(ACTIVE)<MAX_ACTIVE and TOTAL<MAX_TRADES:
                        ACTIVE.append(r); TOTAL+=1
                        tg(f"🚀 NEW {r['side']} {r['symbol']} @{r['entry']} SL {r['sl']}({r['slp']}%) T1 {r['t1']} T2 {r['t2']} | {r['reason']} S:{r['score']:.1f} | ACTIVE {len(ACTIVE)}/{MAX_ACTIVE} | TOTAL {TOTAL}/{MAX_TRADES}")
                        if len(ACTIVE)>=MAX_ACTIVE: break
        if TOTAL>=MAX_TRADES and len(ACTIVE)==0:
            tg(f"📊 END DAY {datetime.now().date()} Trades {TOTAL}/8 | V23 FINAL"); break
        if datetime.now().hour>=15 and datetime.now().minute>=15:
            tg(f"📊 END DAY TIME UP | TOTAL {TOTAL}/8"); break
        time.sleep(60)
    except Exception as e:
        print(f"Error {e}"); time.sleep(10)
