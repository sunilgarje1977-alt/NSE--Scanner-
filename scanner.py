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
        df=yf.download(s, period="3d", interval="15m", progress=False, auto_adjust=True)
        dfd=yf.download(s, period="20d", interval="1d", progress=False, auto_adjust=True)
        if len(df)<20 or len(dfd)<10:
            return None
        
        price=float(df['Close'].iloc[-1])
        if not 30 <= price <= 5000:
            return None

        # 3 Candle Breakout 0.3%
        high3=float(df['High'].iloc[-4:-1].max())
        bo=((price-high3)/high3)*100
        if bo < 0.3:
            return None

        # Smallest Candle SL
        prev3=df.iloc[-4:-1]
        sl=float(prev3.loc[(prev3['Close']-prev3['Open']).abs().idxmin()]['Low'])
        if price <= sl:
            return None

        # Bullish Candle - Fake Breakout नको
        if float(df['Close'].iloc[-1]) <= float(df['Open'].iloc[-1]):
            return None

        # EMA 9 > 15
        ema9=float(df['Close'].ewm(9).mean().iloc[-1])
        ema15=float(df['Close'].ewm(15).mean().iloc[-1])
        if ema9 <= ema15:
            return None
        
        # RSI 50+
        delta=df['Close'].diff()
        gain=delta.where(delta>0,0).rolling(14).mean()
        loss=-delta.where(delta<0,0).rolling(14).mean()
        rs=gain/loss
        rsi=100-(100/(1+rs))
        rsi_last=float(rsi.iloc[-1])
        if rsi_last < 50:
            return None

        tgt=price+(price-sl)*2
        tgt5=price+(price-sl)*5
        return {"sym":s.replace(".NS",""),"entry":price,"sl":sl,"tgt":tgt,"tgt5":tgt5,"bo":bo,"rsi":rsi_last}
    except:
        return None

# 100 Best NSE Stock - Trading साठी
S=["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS","ITC.NS","LT.NS","MARUTI.NS","TITAN.NS","TATAMOTORS.NS","ADANIENT.NS","POWERGRID.NS","ONGC.NS","NTPC.NS","BAJFINANCE.NS","JSWSTEEL.NS","TATASTEEL.NS","ADANIPORTS.NS","HINDALCO.NS","BPCL.NS","EICHERMOT.NS","CIPLA.NS","DIVISLAB.NS","BRITANNIA.NS","HEROMOTOCO.NS","APOLLOHOSP.NS","TECHM.NS","INDUSINDBK.NS","M&M.NS","SBILIFE.NS","HDFCLIFE.NS","DLF.NS","GODREJPROP.NS","INDIGO.NS","GSFC.NS","GNFC.NS","BLSE.NS","REPL.NS","XTRANET.NS","RRKABEL.NS","SUZLON.NS","IRCTC.NS","HAL.NS","BEL.NS","RVNL.NS","IRFC.NS","PRAKASH.NS","KLBRENG-B.NS","HIMATSEIDE.NS","TARAPUR.NS"]*2

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist).strftime("%H:%M:%S")

print(f"Scanning {len(S)} Stocks...")
with ThreadPoolExecutor(max_workers=8) as ex:
    res=[r for r in ex.map(chk, S) if r]
    res=sorted(res,key=lambda x:x['bo'],reverse=True)[:6]

if res:
    msg=f"🚀 *TRADING SCAN {now}*\nActive:{len(res)}/2 Done:0/6\n\n"
    for t in res:
        msg+=f"🟢 *{t['sym']}* ₹{t['entry']:.1f} | BO:{t['bo']:.2f}% RSI:{t['rsi']:.0f}\nSL:{t['sl']:.1f} T:{t['tgt']:.1f} T5:{t['tgt5']:.1f}\n\n"
else:
    msg=f"📊 Scan {now} Active:0/2 Done:0/6 No Trade >0.4% (15m)"

tg(msg)
print(msg)
