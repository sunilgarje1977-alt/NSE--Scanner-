import os, pandas as pd
from SmartApi import SmartConnect
import pyotp
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

def clean(s): return os.getenv(s,"").strip()

obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype'].isin(['EQ']))]
tokens=nse[['token','symbol']].values.tolist()[:1000]

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    return 100-(100/(1+g/l))

def backtest_one(item):
    token,sym=item
    try:
        # 30 Days Data
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":(datetime.now()-timedelta(days=35)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not data or 'data' not in data or len(data['data'])<200: return None
        df=pd.DataFrame(data['data'],columns=['t','o','h','l','c','v'])
        df['ema9']=df['c'].ewm(span=9).mean()
        df['ema15']=df['c'].ewm(span=15).mean()
        df['rsi']=calc_rsi(df['c'])

        daily=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_DAY","fromdate":(datetime.now()-timedelta(days=45)).strftime("%Y-%m-%d 09:15"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not daily or 'data' not in daily: return None
        ddf=pd.DataFrame(daily['data'],columns=['t','o','h','l','c','v'])

        signals=0; wins=0; sl=0; pnl=0

        for i in range(30, len(df)-5):
            c=df.iloc[i]; p=df.iloc[i-1]
            # 10D Check - त्या दिवशीच्या आधीचे 10 दिवस
            try:
                day_idx = int(i / 75) # 75 = 5min candles per day
                if day_idx < 11: continue
                base=ddf.iloc[day_idx-11:day_idx-1]
                high10=base['h'].max(); low10=base['l'].min()
                rng=(high10-low10)/low10*100
                # BACKTEST साठी 3-5% Filter लावायचा का?
                # तुला TOP 10 हवा असेल तर हा Filter काढ - नाहीतर 3623 ऐवजी 50च Signal येईल
                # if rng <3 or rng >5: continue # <-- हा Comment कर TOP 10 साठी
            except: continue

            ema9=df['ema9'].iloc[i]; ema15=df['ema15'].iloc[i]
            ema9_pr=df['ema9'].iloc[i-1]; ema15_pr=df['ema15'].iloc[i-1]
            cross_up=ema9_pr<=ema15_pr and ema9>ema15
            cross_down=ema9_pr>=ema15_pr and ema9<ema15

            body=abs(c['c']-c['o']); rng_c=c['h']-c['l'] if c['h']!=c['l'] else 1
            maru=body/rng_c>=0.6

            is_buy = cross_up and c['rsi']>=55 and maru
            is_sell = cross_down and c['rsi']<=45 and maru

            if is_buy or is_sell:
                signals+=1
                entry=c['c']
                # पुढचे 5 दिवसात TGT/SL लागतोय का?
                future=df.iloc[i+1:i+6]
                if len(future)==0: continue
                if is_buy:
                    sl_price=c['l']; tgt=entry+(entry-sl_price)*2.5
                    hit_tgt = (future['h']>=tgt).any()
                    hit_sl = (future['l']<=sl_price).any()
                else:
                    sl_price=c['h']; tgt=entry-(sl_price-entry)*2.5
                    hit_tgt = (future['l']<=tgt).any()
                    hit_sl = (future['h']>=sl_price).any()

                if hit_tgt and not hit_sl:
                    wins+=1; pnl+=2.5
                elif hit_sl:
                    sl+=1; pnl-=1
                else:
                    # 5 दिवसात काहीच नाही - No Result
                    pass

        if signals>0:
            winrate = wins/signals*100 if signals>0 else 0
            return {"Symbol":sym, "Total":signals, "Wins":wins, "SL":sl, "WinRate":round(winrate,1), "PnL":round(pnl,1)}
    except Exception as e:
        return None

print("BACKTEST START - 1000 STOCKS | 30 DAYS...")
results=[]
with ThreadPoolExecutor(max_workers=40) as ex:
    futs={ex.submit(backtest_one,t):t for t in tokens}
    for f in as_completed(futs):
        r=f.result()
        if r: results.append(r)

df_res=pd.DataFrame(results).sort_values(by="PnL", ascending=False)
print(f"\nTotal Stocks: {len(df_res)}")
print(f"Total Signals: {df_res['Total'].sum()}")
print(f"Avg WinRate: {df_res['WinRate'].mean():.1f}%\n")
print("TOP 10:")
print(df_res.head(10).to_string(index=False))

# Telegram ला पाठव
try:
    import requests
    bot=clean("TELEGRAM_BOT_TOKEN"); chat=clean("TELEGRAM_CHAT_ID")
    top10=df_res.head(10)
    msg=f"📊 *NSE 1000 BACKTEST - 30 DAYS*\nTotal Stocks: {len(df_res)}\nTotal Signals: {df_res['Total'].sum()}\nAvg WinRate: {df_res['WinRate'].mean():.1f}%\n\n🏆 TOP 10:\n"
    for _, row in top10.iterrows():
        msg+=f"{row['Symbol']} - {row['Total']} Sig - {row['WinRate']}% - {row['PnL']} PnL\n"
    requests.post(f"https://api.tele
