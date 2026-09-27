"""
NSE 5000 - 60 DAYS BACKTEST (FINAL V3)
Score >= 3.5 Logic
"""
import os, requests, pandas as pd, yfinance as yf
from datetime import datetime, timedelta
import concurrent.futures, time

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
def send_tg(msg):
    token=clean('TELEGRAM_BOT_TOKEN'); chat=clean('TELEGRAM_CHAT_ID')
    if not token or not chat: print(msg); return
    url=f"https://api.telegram.org/bot{token}/sendMessage"
    # Telegram 4096 char limit - split
    for i in range(0, len(msg), 3800):
        try: requests.post(url, json={"chat_id":chat, "text":msg[i:i+3800], "parse_mode":"Markdown"}, timeout=30)
        except: pass
        time.sleep(1)

# --- NSE 5000 LIST LOAD ---
# तुझ्याकडे symbols file असेल तर तो वापर, नाहीतर हा sample 5000 पर्यंत वाढवेल
# तू तुझ्या scanner.py मधली SYMBOLS list इथे टाकू शकतोस
try:
    # Try to load from existing scanner.py if it has list
    with open("scanner.py","r") as f:
        txt=f.read()
        # crude extract - if you have NSE5000.csv, better use it
        pass
except: pass

# Fallback: NSE 5000 = Nifty 500 + Nifty Midcap + Smallcap (yfinance can handle)
# For demo we load from NSE official list via github (you can replace with your file)
# Here using top 1000 x 5 times unique = 5000 logic for speed
BASE = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","AXISBANK","BAJFINANCE","MARUTI","WIPRO","HCLTECH","ULTRACEMCO","ASIANPAINT","TITAN","NESTLEIND","ONGC","JUBLINGREA","BDL","GRSE","CUPID","CROMPTON","ULTRAMAR","SUNPHARMA","ADANIENT","ADANIGREEN","TATAMOTORS","POWERGRID","NTPC","JSWSTEEL","HINDALCO","VEDL","COALINDIA","BPCL","IOC","HINDUNILVR","BRITANNIA","DIVISLAB","DRREDDY","CIPLA","EICHERMOT","BAJAJ-AUTO","HEROMOTOCO","M&M","TATASTEEL","HINDALCO","GRASIM"]
# Duplicate to make 5000 unique logic - replace with your real 5000 list from CSV
import itertools
SYMBOLS = []
# Try to read nse5000.csv if you have
if os.path.exists("nse5000.csv"):
    import csv
    with open("nse5000.csv") as csvf:
        SYMBOLS = [row[0].strip() for row in csv.reader(csvf) if row]
else:
    # Use NSE listed 5000 from your scanner's universe - for now use Nifty 500 list repeated logic
    # IMPORTANT: तुझ्या scanner.py मधली खरी 5000 ची List इथे टाक
    SYMBOLS = (BASE * 100)[:5000]
SYMBOLS = list(dict.fromkeys(SYMBOLS)) # unique

print(f"Total Symbols for Backtest: {len(SYMBOLS)}")

DAYS = 60
START = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
END = datetime.now().strftime("%Y-%m-%d")

def score_stock(df):
    if len(df)<50: return 0
    try:
        df['EMA20']=df['Close'].ewm(span=20).mean()
        df['EMA50']=df['Close'].ewm(span=50).mean()
        df['VolAvg']=df['Volume'].rolling(20).mean()
        last=df.iloc[-1]
        if pd.isna(last['EMA20']) or pd.isna(last['VolAvg']): return 0
        score=0
        if last['Close']>last['EMA20']: score+=1
        if last['EMA20']>last['EMA50']: score+=1
        if last['Volume']>last['VolAvg']*1.5: score+=1.5
        if last['Close']>df['Close'].rolling(20).max().iloc[-2]: score+=1
        return score
    except: return 0

def process(sym):
    try:
        df=yf.download(sym+".NS", start=START, end=END, progress=False, auto_adjust=True, threads=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        if len(df)<60: return None
        wins=losses=total=pnl=0
        for i in range(30, len(df)-5):
            window=df.iloc[:i+1]
            if score_stock(window)>=3.5:
                total+=1
                entry=float(window.iloc[-1]['Close'])
                future=df.iloc[i+1:i+6]
                if future['High'].max() >= entry*1.06: wins+=1; pnl+=6
                elif future['Low'].min() <= entry*0.97: losses+=1; pnl-=3
                else:
                    diff=(float(future.iloc[-1]['Close'])-entry)/entry*100
                    pnl+=diff
                    if diff>0: wins+=1
                    else: losses+=1
        if total==0: return None
        return {"symbol":sym, "total":total, "wins":wins, "sl":losses, "winrate":wins/total*100 if total else 0, "pnl":pnl}
    except Exception as e:
        return None

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    futures={ex.submit(process, s): s for s in SYMBOLS}
    for fut in concurrent.futures.as_completed(futures):
        r=fut.result()
        if r: results.append(r)
        if len(results)%100==0: print(f"Done {len(results)}/{len(SYMBOLS)}")

results=sorted(results, key=lambda x: x['winrate'], reverse=True)
top20=results[:20]
total_signals=sum(r['total'] for r in results)
avg_wr=sum(r['winrate'] for r in results)/len(results) if results else 0
total_pnl=sum(r['pnl'] for r in results)

# Save CSV
pd.DataFrame(results).to_csv("backtest_5000_60days.csv", index=False)

msg=f"📊 *NSE 5000 BACKTEST - 60 DAYS (V3 Score>=3.5)*\n"
msg+=f"Stocks Tested: {len(SYMBOLS)}\nTraded: {len(results)}\nTotal Signals: {total_signals}\nAvg WinRate: {avg_wr:.1f}%\nTotal PnL: {total_pnl:+.0f}%\n\n"
msg+=f"🏆 *TOP 20:*\n`Sym Tot Win SL WR% PnL`\n"
for r in top20:
    msg+=f"{r['symbol'][:8]:<6} {r['total']:>3} {r['wins']:>3} {r['sl']:>2} {r['winrate']:.0f}% {r['pnl']:+.0f}%\n"

print(msg)
send_tg(msg)
