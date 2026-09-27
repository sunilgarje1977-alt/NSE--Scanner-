 """
NSE 5000 REAL LIST - 60 DAYS BACKTEST V3
Auto Downloads NSE Official Equity List
"""
import os, requests, pandas as pd, yfinance as yf
from datetime import datetime, timedelta
import concurrent.futures, time, io

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
def send_tg(msg):
    token=clean('TELEGRAM_BOT_TOKEN'); chat=clean('TELEGRAM_CHAT_ID')
    if not token or not chat: print(msg); return
    url=f"https://api.telegram.org/bot{token}/sendMessage"
    for i in range(0, len(msg), 3800):
        try: requests.post(url, json={"chat_id":chat, "text":msg[i:i+3800], "parse_mode":"Markdown"}, timeout=30)
        except Exception as e: print(e)
        time.sleep(1)

# --- 1. REAL NSE LIST DOWNLOAD ---
def get_nse_5000():
    urls = [
        "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
        "https://archives.nseindia.com/content/equities/EQUITY_L.csv",
        "https://raw.githubusercontent.com/prasiddhData/nse_eq_list/main/EQUITY_L.csv"
    ]
    symbols = []
    for url in urls:
        try:
            print(f"Trying {url}")
            r = requests.get(url, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
            if r.status_code==200 and "SYMBOL" in r.text[:100]:
                df = pd.read_csv(io.StringIO(r.text))
                symbols = df['SYMBOL'].dropna().astype(str).str.strip().tolist()
                print(f"Got {len(symbols)} symbols from NSE")
                break
        except Exception as e:
            print(e); continue
    
    # Fallback: If NSE blocks, use Nifty 500 + your scanner's list
    if len(symbols) < 1000:
        print("NSE Blocked - Using Backup Nifty 500 + Midcap List")
        # Backup top 500 from NSE Github
        try:
            r=requests.get("https://raw.githubusercontent.com/kotak-neo/nse-stock-list/main/nse_eq.json", timeout=15)
            if r.ok:
                import json
                data=r.json()
                symbols=[x for x in data][:5000]
        except: pass
        if len(symbols)<500:
            symbols=["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","AXISBANK","BAJFINANCE","MARUTI","WIPRO","HCLTECH","ULTRACEMCO","ASIANPAINT","TITAN","NESTLEIND","ONGC","JUBLINGREA","BDL","GRSE","CUPID","CROMPTON","ULTRAMAR","SUNPHARMA","ADANIENT","ADANIGREEN","TATAMOTORS","POWERGRID","NTPC","JSWSTEEL","HINDALCO","VEDL","COALINDIA","BPCL","IOC","HINDUNILVR","BRITANNIA","DIVISLAB","DRREDDY","CIPLA","EICHERMOT","BAJAJ-AUTO","HEROMOTOCO","M&M","TATASTEEL","GRASIM","SBILIFE","HDFCLIFE","ICICIPRULI","BAJAJFINSV","BAJAJHFL","ADANIPORTS","ADANIPOWER","TATAPOWER","NHPC","SJVN","IRCTC","IRFC","RVNL","HAL","BEL","MAZDOCK","COCHINSHIP","PFC","RECLTD"]*20

    # Clean & Unique - remove ETFs etc if needed, keep only EQ
    symbols = [s for s in symbols if s.isalnum() or "-" in s]
    symbols = list(dict.fromkeys(symbols))[:5000]
    return symbols

SYMBOLS = get_nse_5000()
print(f"FINAL SYMBOLS FOR BACKTEST: {len(SYMBOLS)}")

DAYS = 60
START = (datetime.now() - timedelta(days=95)).strftime("%Y-%m-%d")
END = datetime.now().strftime("%Y-%m-%d")

def score_stock(df):
    if len(df)<50: return 0
    try:
        df['EMA20']=df['Close'].ewm(span=20).mean()
        df['EMA50']=df['Close'].ewm(span=50).mean()
        df['VolAvg']=df['Volume'].rolling(20).mean()
        last=df.iloc[-1]
        if pd.isna(last['EMA20']) or pd.isna(last['VolAvg']) or last['VolAvg']==0: return 0
        score=0
        if last['Close']>last['EMA20']: score+=1
        if last['EMA20']>last['EMA50']: score+=1
        if last['Volume']>last['VolAvg']*1.5: score+=1.5
        if last['Close']>=df['Close'].rolling(20).max().iloc[-2]*0.998: score+=1
        return score
    except: return 0

def process(sym):
    try:
        df=yf.download(sym+".NS", start=START, end=END, progress=False, auto_adjust=True, threads=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        if len(df)<60: return None
        wins=losses=total=pnl=0
        for i in range(35, len(df)-5):
            window=df.iloc[:i+1]
            if score_stock(window)>=3.5:
                total+=1
                entry=float(window.iloc[-1]['Close'])
                future=df.iloc[i+1:i+6]
                hi=future['High'].max(); lo=future['Low'].min()
                if hi >= entry*1.06: wins+=1; pnl+=6
                elif lo <= entry*0.97: losses+=1; pnl-=3
                else:
                    diff=(float(future.iloc[-1]['Close'])-entry)/entry*100
                    pnl+=diff
                    if diff>0: wins+=1
                    else: losses+=1
        if total==0: return None
        return {"symbol":sym, "total":total, "wins":wins, "sl":losses, "winrate":wins/total*100, "pnl":pnl}
    except: return None

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    for r in ex.map(process, SYMBOLS):
        if r: 
            results.append(r)
            if len(results)%50==0: print(f"Progress {len(results)}/{len(SYMBOLS)} Traded found")

results=sorted(results, key=lambda x: x['winrate'], reverse=True)
pd.DataFrame(results).to_csv("backtest_5000_60days.csv", index=False)

top20=results[:20]
total_signals=sum(r['total'] for r in results)
avg_wr=sum(r['winrate'] for r in results)/len(results) if results else 0
total_pnl=sum(r['pnl'] for r in results)

msg=f"📊 *NSE REAL {len(SYMBOLS)} STOCKS BACKTEST - 60 DAYS (V3 Score>=3.5)*\n"
msg+=f"Tested: {len(SYMBOLS)}\nTraded: {len(results)}\nSignals: {total_signals}\nAvg WR: {avg_wr:.1f}%\nTotal PnL: {total_pnl:+.0f}%\n\n"
msg+=f"🏆 *TOP 20:*\n`Sym     T  W SL WR% PnL`\n"
for r in top20:
    msg+=f"{r['symbol'][:8]:<7} {r['total']:>3} {r['wins']:>2} {r['sl']:>2} {r['winrate']:.0f}% {r['pnl']:+.0f}%\n"

print(msg)
send_tg(msg)
