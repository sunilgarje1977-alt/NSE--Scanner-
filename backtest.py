# FILE: backtest_60_combo.py - 60 DAYS NSE 1000 COMBO BACKTEST
import os, pandas as pd, pyotp
from SmartApi import SmartConnect
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

def clean(s): return os.getenv(s,"").strip()
obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype'].isin(['EQ']))]
tokens=nse[['token','symbol']].values.tolist()[:1000]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    rs=g/l; return 100-(100/(1+rs))

def backtest_one(item):
    token,sym=item
    try:
        data=obj.getCandleData({
            "exchange":"NSE","symboltoken":token,"interval":"ONE_DAY",
            "fromdate":(datetime.now()-timedelta(days=90)).strftime("%Y-%m-%d 09:15"),
            "todate":datetime.now().strftime("%Y-%m-%d 15:30")
        })
        if not data or 'data' not in data or len(data['data'])<65: return None
        df=pd.DataFrame(data['data'],columns=['t','o','h','l','c','v'])
        df=df.tail(60)
        df['ema9']=df['c'].ewm(span=9).mean(); df['ema15']=df['c'].ewm(span=15).mean(); df['rsi']=calc_rsi(df['c'])

        wins=0; total=0
        for i in range(11, len(df)-5):
            curr=df.iloc[i]; prev=df.iloc[i-1]; base=df.iloc[i-10:i]

            # Logic 1: Gap >2%
            gap=(curr['o']-prev['c'])/prev['c']*100 if prev['c']!=0 else 0
            gap_ok=gap>=2

            # Logic 2: Vol 3X
            avg_vol=base['v'].mean()
            vol_mult=curr['v']/avg_vol if avg_vol>0 else 0
            vol_ok=vol_mult>=2.5

            # Logic 3: 10D 3-5% Breakout
            high10=base['h'].max(); low10=base['l'].min()
            rng10=(high10-low10)/low10*100 if low10!=0 else 0
            bo_ok = (3<=rng10<=5) and (curr['c']>high10)

            # Logic 4: EMA Cross + Marubozu + RSI
            ema_cross = df['ema9'].iloc[i-1] <= df['ema15'].iloc[i-1] and df['ema9'].iloc[i] > df['ema15'].iloc[i]
            body=abs(curr['c']-curr['o']); rng_c=curr['h']-curr['l'] if curr['h']!=curr['l'] else 1
            maru=body/rng_c>=0.5
            ema_ok=ema_cross and curr['rsi']>=55 and maru

            score = (1 if gap_ok else 0) + (1 if vol_ok else 0) + (2 if bo_ok else 0) + (1 if ema_ok else 0)

            if score>=2: # COMBO SCORE >=2
                total+=1
                entry=curr['c']; sl=curr['l']; tgt=entry+(entry-sl)*2.5
                future=df.iloc[i+1:i+6]
                if not future.empty and (future['h']>=tgt).any():
                    wins+=1

        if total>0:
            return {"Symbol":sym, "Signals":total, "Wins":wins, "WinRate":round(wins/total*100,1), "AvgVolX":round(df['v'].tail(20).mean()/df['v'].mean(),1)}
    except: return None

results=[]
print("Scanning NSE 1000 - 60 Days Combo Logic...")
with ThreadPoolExecutor(max_workers=30) as ex:
    futs={ex.submit(backtest_one,t):t for t in tokens}
    for f in as_completed(futs):
        r=f.result()
        if r: results.append(r)

if results:
    df=pd.DataFrame(results)
    df=df.sort_values(by='WinRate', ascending=False)
    print(f"\n===== 60 DAYS COMBO BACKTEST - NSE 1000 =====")
    print(f"Stocks Found: {len(df)} / 1000")
    print(f"Total Signals (Score>=2): {df['Signals'].sum()}")
    print(f"Avg WinRate: {df['WinRate'].mean():.1f}%")
    print(f"\n--- TOP 20 JACKPOT STOCKS ---")
    print(df.head(20).to_string(index=False))
    df.to_csv("60days_combo_results.csv", index=False)
    print("\nFile Saved: 60days_combo_results.csv")
else:
    print("No Signals")
