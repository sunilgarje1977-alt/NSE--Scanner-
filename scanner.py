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
        df=yf.download(s.strip(), period="5d", interval="5m", progress=False, auto_adjust=True)
        if len(df)<40:
            return None
        last=df.iloc[-1]
        prev3=df.iloc[-4:-1]
        price=float(last['Close'])
        if not 20 <= price <= 6000:
            return None

        # 1. 3 Candle + Day High - MUST
        three_high=float(prev3['High'].max())
        if price <= three_high:
            return None
        bo3=((price-three_high)/three_high)*100
        if bo3 < 0.15:
            return None

        today = df.iloc[-1].name.date()
        today_df = df[df.index.date == today]
        day_high = float(today_df.iloc[:-1]['High'].max()) if len(today_df)>1 else three_high
        if price <= day_high:
            return None

        # 2. Volume - 1.1x केले - 1.3 ऐवजी - जास्त Trade साठी
        avg_vol = float(df['Volume'].iloc[-20:-1].mean())
        curr_vol = float(last['Volume'])
        if curr_vol < avg_vol * 1.1:
            return None

        # 3. Candle Body - 40% केले - 50 ऐवजी
        body = float(last['Close']) - float(last['Open'])
        if body <= 0:
            return None
        cr = float(last['High']) - float(last['Low'])
        if cr == 0:
            return None
        if (body/cr)*100 < 35:
            return None

        # 4. SL + Bullish
        sl=float(prev3.loc[(prev3['Close']-prev3['Open']).abs().idxmin()]['Low'])
        if price <= sl or ((price-sl)/price)*100 > 2.8:
            return None

        # 5. EMA + RSI 52 केले - 55 ऐवजी
        ema9=float(df['Close'].ewm(9).mean().iloc[-1])
        ema15=float(df['Close'].ewm(15).mean().iloc[-1])
        if ema9 <= ema15:
            return None
        delta=df['Close'].diff()
        gain=delta.where(delta>0,0).rolling(14).mean()
        loss=-delta.where(delta<0,0).rolling(14).mean()
        rsi=float((100-(100/(1+gain/loss))).iloc[-1])
        if rsi < 52:
            return None

        tgt=price+(price-sl)*2
        tgt5=price+(price-sl)*5
        volx=curr_vol/avg_vol if avg_vol>0 else 0
        return {"sym":s.replace(".NS","").strip(),"entry":price,"sl":sl,"tgt":tgt,"tgt5":tgt5,"bo":bo3,"volx":volx,"rsi":rsi}
    except:
        return None

try:
    with open("stocks.txt") as f:
        S=[l.strip() for l in f if l.strip()][:1000]
except:
    S=["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS","ITC.NS","LT.NS","MARUTI.NS","TITAN.NS","TATAMOTORS.NS","ADANIENT.NS","POWERGRID.NS","ONGC.NS","NTPC.NS","BAJFINANCE.NS","JSWSTEEL.NS","TATASTEEL.NS","ADANIPORTS.NS","HINDALCO.NS","BPCL.NS","EICHERMOT.NS","CIPLA.NS","DIVISLAB.NS","BRITANNIA.NS","HEROMOTOCO.NS","APOLLOHOSP.NS","TECHM.NS","M&M.NS","DLF.NS","GODREJPROP.NS","INDIGO.NS","GSFC.NS","BLSE.NS","REPL.NS","XTRANET.NS","RRKABEL.NS","SUZLON.NS","HAL.NS","BEL.NS"]*24

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist).strftime("%H:%M:%S")

with ThreadPoolExecutor(max_workers=20) as ex:
    res=[r for r in ex.map(chk, S) if r]
    res=sorted(res,key=lambda x:x['bo']+x['volx'],reverse=True)[:3]

if res:
    msg=f"STRONG 2-3 TRADE {now} 5M\n1000 Scan | 3C+DayHigh+Vol1.1x+RSI52\n\n"
    for t in res:
        msg+=f"{t['sym']} ENTRY {t['entry']:.1f} BO {t['bo']:.2f}% Vol {t['volx']:.1f}x RSI {t['rsi']:.0f}\nSL {t['sl']:.1f} T1 {t['tgt']:.1f} T5 {t['tgt5']:.1f}\n\n"
else:
    msg=f"Scan {now} - 1000 Scan Done No Trade\nFilter 3C+DayHigh+Vol1.1x+Body35%+RSI52"

tg(msg)
print(msg)
