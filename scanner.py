import yfinance as yf, requests, os, pytz
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

B=os.getenv("TELEGRAM_BOT_TOKEN")
C=os.getenv("TELEGRAM_CHAT_ID")

def tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{B}/sendMessage",data={"chat_id":C,"text":m,"parse_mode":"Markdown"},timeout=10)
    except:
        pass

def chk(s):
    try:
        df=yf.download(s, period="5d", interval="15m", progress=False, auto_adjust=True)
        if len(df)<30:
            return None
        
        last=df.iloc[-1]
        prev3=df.iloc[-4:-1]
        price=float(last['Close'])
        
        if not 30 <= price <= 5000:
            return None

        # === CONDITION 1: मागील 3 Candle High Breakout ===
        three_high=float(prev3['High'].max())
        if price <= three_high:
            return None
        bo3=((price-three_high)/three_high)*100
        if bo3 < 0.3:
            return None

        # === CONDITION 2: Day High Breakout === NEW
        # आजचा दिवस - आजचा High (Current Candle सोडून)
        today = df.iloc[-1].name.date()
        today_df = df[df.index.date == today]
        if len(today_df) > 1:
            day_high = float(today_df.iloc[:-1]['High'].max())
        else:
            # आजचा पहिलाच Candle असेल तर कालचा Day High
            day_high = float(df.iloc[-27:-1]['High'].max()) if len(df)>27 else three_high
        
        if price <= day_high:
            return None
        bo_day=((price-day_high)/day_high)*100
        if bo_day < 0.2: # Day High 0.2% तरी तोडला पाहिजे
            return None

        # === CONDITION 3: Smallest Candle SL ===
        sl=float(prev3.loc[(prev3['Close']-prev3['Open']).abs().idxmin()]['Low'])
        if price <= sl:
            return None
        if ((price-sl)/price)*100 > 2.5: # Risk जास्त नको
            return None

        # === CONDITION 4: Bullish + EMA + RSI ===
        if float(last['Close']) <= float(last['Open']):
            return None
        ema9=float(df['Close'].ewm(9).mean().iloc[-1])
        ema15=float(df['Close'].ewm(15).mean().iloc[-1])
        if ema9 <= ema15:
            return None
        
        delta=df['Close'].diff()
        gain=delta.where(delta>0,0).rolling(14).mean()
        loss=-delta.where(delta<0,0).rolling(14).mean()
        rsi=100-(100/(1+gain/loss))
        rsi_last=float(rsi.iloc[-1])
        if rsi_last < 52:
            return None

        tgt=price+(price-sl)*2
        tgt5=price+(price-sl)*5
        return {"sym":s.replace(".NS",""),"entry":price,"sl":sl,"tgt":tgt,"tgt5":tgt5,"bo3":bo3,"bo_day":bo_day,"day_high":day_high,"three_high":three_high,"rsi":rsi_last}
    except:
        return None

S=["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS","ITC.NS","LT.NS","MARUTI.NS","TITAN.NS","TATAMOTORS.NS","ADANIENT.NS","POWERGRID.NS","ONGC.NS","NTPC.NS","BAJFINANCE.NS","JSWSTEEL.NS","TATASTEEL.NS","ADANIPORTS.NS","HINDALCO.NS","BPCL.NS","EICHERMOT.NS","CIPLA.NS","DIVISLAB.NS","BRITANNIA.NS","HEROMOTOCO.NS","APOLLOHOSP.NS","TECHM.NS","INDUSINDBK.NS","M&M.NS","SBILIFE.NS","HDFCLIFE.NS","DLF.NS","GODREJPROP.NS","INDIGO.NS","GSFC.NS","GNFC.NS","BLSE.NS","REPL.NS","XTRANET.NS","RRKABEL.NS","SUZLON.NS","IRCTC.NS","HAL.NS","BEL.NS"]*2

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist).strftime("%H:%M:%S")

with ThreadPoolExecutor(max_workers=8) as ex:
    res=[r for r in ex.map(chk, S) if r]
    res=sorted(res,key=lambda x:x['bo3']+x['bo_day'],reverse=True)[:2]

if res:
    msg=f"🚀 *3 CANDLE + DAY HIGH BREAKOUT {now}*\n\n"
    for t in res:
        msg+=f"🟢 *{t['sym']}* ₹{t['entry']:.1f}\n3C High:{t['three_high']:.1f} BO:{t['bo3']:.2f}%\nDay High:{t['day_high']:.1f} BO:{t['bo_day']:.2f}%\nSL:{t['sl']:.1f} T:{t['tgt']:.1f} T5:{t['tgt5']:.1f} RSI:{t['rsi']:.0f}\n\n"
else:
    msg=f"📊 Scan {now} Active:0/2 Done:0/6 No Trade - 3Candle+DayHigh+0.3% Filter"

tg(msg)
print(msg)
