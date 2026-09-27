import os, json, pyotp, urllib.request, pandas as pd, requests
from datetime import datetime, timedelta
from SmartApi import SmartConnect
import time

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
API_KEY=clean('ANGEL_API_KEY'); CLIENT_ID=clean('ANGEL_CLIENT_ID'); PWD=clean('ANGEL_PASSWORD'); TOTP_SECRET=clean('ANGEL_TOTP_SECRET')

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f: master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

# Test Universe - Top 50 Active
UNIVERSE=["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","HAL","BEL","BDL","RVNL","NHPC","PFC","RECLTD","IRFC","TATASTEEL","BHARTIARTL","ITC","LT","M&M","SBIN","ADANIENT","ADANIPORTS","TATAPOWER","TATAMOTORS","ZOMATO","PAYTM","IRCTC","VBL","TITAN","DMART","BAJFINANCE","KDDL","NITCO","GREENPANEL","NETWEB","ALLCARGO","JKCEMENT","MAWANASUG","TIPSFILMS","PONNIERODE"]

def get_hist(token, days=70):
    try:
        fromdate=(datetime.now()-timedelta(days=days)).strftime("%Y-%m-%d %H:%M")
        todate=datetime.now().strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"ONE_DAY","fromdate":fromdate,"todate":todate})['data']
        df=pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        return df
    except: return None

def check_signal_on_day(df, idx):
    # idx is the day we check signal on
    if idx < 40: return None
    sub=df.iloc[:idx+1].copy()
    if len(sub)<40: return None
    sub['EMA9']=sub['Close'].ewm(9).mean(); sub['EMA15']=sub['Close'].ewm(15).mean()
    sub['TP']=(sub['High']+sub['Low']+sub['Close'])/3; sub['VWAP']=(sub['TP']*sub['Volume']).cumsum()/sub['Volume'].cumsum()
    delta=sub['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
    sub['RSI']=100-(100/(1+gain/loss)); sub['MACD']=sub['Close'].ewm(12).mean()-sub['Close'].ewm(26).mean()

    c=sub.iloc[-1]; c3h=sub['High'].iloc[-4:-1].max(); c3l=sub['Low'].iloc[-4:-1].min()
    vol_avg=sub['Volume'].iloc[-11:-1].mean()

    buy_score=sum([c['Close']>c3h, c['EMA9']>c['VWAP'], c['EMA15']>c['VWAP'], c['RSI']>55, sub['MACD'].iloc[-1]>0, c['Volume']>vol_avg*1.0])
    sell_score=sum([c['Close']<c3l, c['EMA9']<c['VWAP'], c['EMA15']<c['VWAP'], c['RSI']<45, sub['MACD'].iloc[-1]<0, c['Volume']>vol_avg*1.0])

    if buy_score>=4: # 5/7 पेक्षा थोडं कमी Backtest साठी
        sl=min(c3l, c['Close']*0.97); r=c['Close']-sl
        return {"type":"BUY","entry":c['Close'],"sl":sl,"t1":c['Close']+r*2,"t2":c['Close']+r*5}
    if sell_score>=4:
        sl=max(c3h, c['Close']*1.03); r=sl-c['Close']
        return {"type":"SELL","entry":c['Close'],"sl":sl,"t1":c['Close']-r*2,"t2":c['Close']-r*5}
    return None

# ===== 60 DAYS BACKTEST =====
results=[]
for sym in UNIVERSE:
    token=token_map.get(sym)
    if not token: continue
    df=get_hist(token, 90)
    if df is None or len(df)<60: continue
    time.sleep(0.3)
    # Last 60 days
    for i in range(len(df)-60, len(df)-5): # 5 days forward result बघण्यासाठी
        sig=check_signal_on_day(df, i)
        if sig:
            entry=sig['entry']
            # पुढचे 10 दिवसात काय झालं?
            future=df.iloc[i+1:i+11]
            if len(future)==0: continue
            hit_t1=False; hit_sl=False; hit_t2=False; pnl=0

            for _, f in future.iterrows():
                if sig['type']=='BUY':
                    if f['Low']<=sig['sl']: hit_sl=True; pnl=-1; break
                    if f['High']>=sig['t1']: hit_t1=True
                    if f['High']>=sig['t2']: hit_t2=True; pnl=3.5; break # 50% 2R + 50% 5R = 3.5R avg
                else:
                    if f['High']>=sig['sl']: hit_sl=True; pnl=-1; break
                    if f['Low']<=sig['t1']: hit_t1=True
                    if f['Low']<=sig['t2']: hit_t2=True; pnl=3.5; break
            if hit_t1 and not hit_sl and not hit_t2: pnl=1.0 # फक्त T1 लागला

            results.append({"date":df.iloc[i]['Time'],"sym":sym,"type":sig['type'],"pnl_R":pnl,"hit_t1":hit_t1,"hit_t2":hit_t2,"hit_sl":hit_sl})
    print(f"{sym} Done - Signals {len([r for r in results if r['sym']==sym])}")

# SUMMARY
import pandas as pd
rdf=pd.DataFrame(results)
if len(rdf)==0:
    print("No Signals in 60 Days")
else:
    win=(rdf['pnl_R']>0).sum(); loss=(rdf['pnl_R']<0).sum(); total=len(rdf)
    winrate=win/total*100 if total>0 else 0
    avg_r=rdf['pnl_R'].mean()
    print(f"\n===== 60 DAYS BACKTEST RESULT =====")
    print(f"Total Trades: {total}")
    print(f"Win: {win} Loss: {loss} Winrate: {winrate:.1f}%")
    print(f"Avg R per Trade: {avg_r:.2f}R")
    print(f"Expected on 1Lac Capital (1% Risk per trade): {avg_r*total:.1f}% approx")
    print(rdf.head(20))
    rdf.to_csv("backtest_60days.csv", index=False)

    # Telegram
    try:
        TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN'); TELE_CHAT=clean('TELEGRAM_CHAT_ID')
        msg=f"📊 *60 DAYS BACKTEST*\n\nTotal: {total}\nWin: {win} Loss: {loss}\nWinrate: {winrate:.1f}%\nAvg: {avg_r:.2f}R\n\nTop: {rdf['sym'].value_counts().head(3).to_dict()}"
        requests.get(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", params={"chat_id":TELE_CHAT, "text":msg, "parse_mode":"Markdown"})
    except: pass
