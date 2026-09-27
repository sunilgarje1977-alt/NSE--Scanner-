import os, json, pyotp, urllib.request, pandas as pd
from datetime import datetime, timedelta
from SmartApi import SmartConnect

def clean(k):
    return os.getenv(k,"").strip().strip('"').strip("'")
API_KEY=clean('ANGEL_API_KEY')
CLIENT_ID=clean('ANGEL_CLIENT_ID')
PWD=clean('ANGEL_PASSWORD')
TOTP_SECRET=clean('ANGEL_TOTP_SECRET')

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f:
    master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

# Top 20 Stock for Fast Backtest
TEST_STOCKS=["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","AXISBANK","SBIN","BHARTIARTL","ITC","LT","M&M","TATAMOTORS","HAL","BEL","BDL","RVNL","NHPC","PFC","RECLTD","IRFC"]

def supertrend_dir(df):
    hl2=(df['High']+df['Low'])/2
    tr=pd.concat([(df['High']-df['Low']),(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(10).mean()
    lower=hl2-3*atr; upper=hl2+3*atr
    direction=pd.Series(1,index=df.index)
    for i in range(1,len(df)):
        if df['Close'].iloc[i]<=lower.iloc[i-1]: direction.iloc[i]=1
        elif df['Close'].iloc[i]>=upper.iloc[i-1]: direction.iloc[i]=-1
        else: direction.iloc[i]=direction.iloc[i-1]
    df['ATR']=atr; df['LOWER']=lower; df['UPPER']=upper
    return direction

def backtest_one(sym, token):
    try:
        to_date=datetime.now(); from_date=to_date-timedelta(days=35)
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")})['data']
        df=pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<100: return []
        df['EMA9']=df['Close'].ewm(span=9).mean()
        df['EMA15']=df['Close'].ewm(span=15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3
        df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff()
        gain=delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        df['MACD']=df['Close'].ewm(span=12).mean()-df['Close'].ewm(span=26).mean()
        df['DIR']=supertrend_dir(df)

        trades=[]
        # Last 30 days - daily loop
        for i in range(50, len(df)-15):
            c1=df.iloc[i-3]; c4=df.iloc[i]
            avg_vol=df['Volume'].iloc[i-10:i-1].mean()
            buy_score=sum([c4['Close']>c1['High'], c4['EMA9']>c4['VWAP'], c4['EMA15']>c4['VWAP'], df['DIR'].iloc[i]<0, c4['RSI']>50, df['MACD'].iloc[i]>0, c4['Volume']>avg_vol*1.1])
            sell_score=sum([c4['Close']<c1['Low'], c4['EMA9']<c4['VWAP'], c4['EMA15']<c4['VWAP'], df['DIR'].iloc[i]>0, c4['RSI']<50, df['MACD'].iloc[i]<0, c4['Volume']>avg_vol*1.1])

            if buy_score>=5 or sell_score>=5:
                entry=c4['Close']
                if buy_score>=5:
                    sl=min(c1['Low'], entry-df['ATR'].iloc[i]*1.5)
                    tgt=entry+(entry-sl)*2
                    # Next 10 candle मध्ये काय झालं?
                    future=df.iloc[i+1:i+15]
                    win=False; hit="No Exit"
                    for _, f in future.iterrows():
                        if f['High']>=tgt: win=True; hit="TGT"; break
                        if f['Low']<=sl: win=False; hit="SL"; break
                    trades.append({"sym":sym, "type":"BUY", "entry":entry, "sl":sl, "tgt":tgt, "win":win, "hit":hit, "date":c4['Time']})
                else:
                    sl=max(c1['High'], entry+df['ATR'].iloc[i]*1.5)
                    tgt=entry-(sl-entry)*2
                    future=df.iloc[i+1:i+15]
                    win=False; hit="No Exit"
                    for _, f in future.iterrows():
                        if f['Low']<=tgt: win=True; hit="TGT"; break
                        if f['High']>=sl: win=False; hit="SL"; break
                    trades.append({"sym":sym, "type":"SELL", "entry":entry, "sl":sl, "tgt":tgt, "win":win, "hit":hit, "date":c4['Time']})
        return trades
    except Exception as e:
        print(sym, e)
        return []

all_trades=[]
for sym in TEST_STOCKS:
    token=token_map.get(sym)
    if token:
        tr=backtest_one(sym, token)
        all_trades.extend(tr)
        print(f"{sym} -> {len(tr)} Trades")

if all_trades:
    df_tr=pd.DataFrame(all_trades)
    wins=df_tr['win'].sum()
    total=len(df_tr)
    win_rate=wins/total*100 if total else 0
    buy_trades=df_tr[df_tr['type']=='BUY']
    sell_trades=df_tr[df_tr['type']=='SELL']
    print("\n===== 30 DAY BACKTEST RESULT =====")
    print(f"Total Trades: {total}")
    print(f"Wins: {wins} | Loss: {total-wins}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"BUY Trades: {len(buy_trades)} Win Rate: {buy_trades['win'].mean()*100:.1f}%")
    print(f"SELL Trades: {len(sell_trades)} Win Rate: {sell_trades['win'].mean()*100:.1f}%")
    print("\nTop 10 Trades:")
    print(df_tr.head(10).to_string())
    # Save CSV
    df_tr.to_csv("backtest_30day.csv", index=False)
    print("\nCSV Saved: backtest_30day.csv")
else:
    print("No Trades Found in 30 Days")
