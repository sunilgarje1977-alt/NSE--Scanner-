 """
V6 FINAL - 1000Cr+ MarketCap | Top 10 Gainer (BUY+SELL) | Top 10 Loser (BUY+SELL)
Conditions: Notebook 4-Candle Breakout + High Volume + EMA9/15 + VWAP + Supertrend + RSI + MACD
Author: For Boss
"""
import os, json, pyotp, requests, urllib.request, concurrent.futures
import pandas as pd
from datetime import datetime, timedelta
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN')
TELE_CHAT=clean('TELEGRAM_CHAT_ID')
API_KEY=clean('ANGEL_API_KEY')
CLIENT_ID=clean('ANGEL_CLIENT_ID')
PWD=clean('ANGEL_PASSWORD')
TOTP_SECRET=clean('ANGEL_TOTP_SECRET')

def send_tg(msg):
    if not TELE_TOKEN or not TELE_CHAT:
        print(msg); return
    url=f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage"
    for i in range(0,len(msg),3800):
        try:
            requests.post(url, json={"chat_id":TELE_CHAT,"text":msg[i:i+3800],"parse_mode":"Markdown"}, timeout=15)
        except Exception as e:
            print("TG Error",e)

# 1. Angel Login
print("Logging to Angel...")
smart = SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PWD, pyotp.TOTP(TOTP_SECRET).now())
print("Angel Login DONE")

# 2. Scrip Master
if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f:
    master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

# 3. 1000Cr+ List - Duplicate Remove
REAL_1000CR = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","AXISBANK","BAJFINANCE","MARUTI","WIPRO","HCLTECH","ULTRACEMCO","ASIANPAINT","TITAN","ONGC","HAL","BEL","BDL","GRSE","MAZDOCK","RVNL","NHPC","SJVN","IRCTC","COCHINSHIP","BHEL","PFC","RECLTD","IRFC","TATAPOWER","NTPC","POWERGRID","COALINDIA","JSWSTEEL","TATASTEEL","HINDALCO","VEDL","SAIL","JINDALSTEL","NMDC","ADANIENT","ADANIPORTS","ADANIGREEN","ADANIPOWER","JSWENERGY","GAIL","OIL","PETRONET","IGL","MGL","BPCL","IOC","M&M","TATAMOTORS","EICHERMOT","BAJAJ-AUTO","HEROMOTOCO","TVSMOTOR","ASHOKLEY","MRF","BALKRISIND","APOLLOTYRE","BHARATFORG","MOTHERSON","SUNPHARMA","DIVISLAB","DRREDDY","CIPLA","LUPIN","AUROPHARMA","ZYDUSLIFE","ALKEM","TORNTPHARM","IPCALAB","SYNGENE","LAURUSLABS","GLENMARK","BIOCON","SBILIFE","HDFCLIFE","ICICIPRULI","ICICIGI","LICI","BAJAJFINSV","MUTHOOTFIN","CHOLAFIN","SHRIRAMFIN","LICHSGFIN","POONAWALLA","SBICARD","M&MFIN","CREDITACC","DMART","TRENT","PIDILITEX","HAVELLS","VOLTAS","DIXON","KAYNES","AMBER","SYRMA","TATAELXSI","PERSISTENT","COFORGE","MPHASIS","LTIM","LTTS","KPITTECH","TATATECH","TECHM","BSE","MCX","CAMS","CDSL","KFINTECH","IEX","ANGELONE","NUVAMA","MOTILALOFS","HDFCAMC","POLYCAB","KEI","ASTRAL","SUPREMEIND","APLAPOLLO","BOSCHLTD","ABB","SIEMENS","CUMMINSIND","THERMAX","SKFINDIA","TIMKEN","HONAUT","3MINDIA","AIAENG","GRASIM","SHREECEM","ACC","AMBUJACEM","DALBHARAT","JKCEMENT","RAMCOCEM","BANKBARODA","CANBK","PNB","UNIONBANK","INDUSINDBK","FEDERALBNK","IDFCFIRSTB","AUBANK","BANDHANBNK","RBLBANK","IDBI","BANKINDIA","MAHABANK","PAYTM","ZOMATO","NYKAA","DELHIVERY","POLICYBZR","INDIAMART","AFFLE","TANLA","MAPMYINDIA","NAUKRI","ISGEC"]
SYMBOLS = list(dict.fromkeys([s for s in REAL_1000CR if s in token_map]))
print(f"Scanning {len(SYMBOLS)} Stocks (1000Cr+ Filtered)")

def get_gain(sym):
    try:
        token=token_map.get(sym)
        d=smart.ltpData("NSE", sym+"-EQ", token)['data']
        ltp=float(d['ltp']); open_p=float(d.get('open',ltp))
        pct=(ltp-open_p)/open_p*100 if open_p else 0
        return {"symbol":sym, "pct":pct, "price":ltp, "token":token}
    except:
        return None

filtered=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    for r in ex.map(get_gain, SYMBOLS):
        if r: filtered.append(r)

top10_gainers=sorted(filtered,key=lambda x:x['pct'],reverse=True)[:10]
top10_losers=sorted(filtered,key=lambda x:x['pct'])[:10]

def supertrend_dir(df, p=10, m=3):
    hl2=(df['High']+df['Low'])/2
    tr=pd.concat([(df['High']-df['Low']), (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(p).mean()
    upper=hl2+m*atr; lower=hl2-m*atr
    direction=pd.Series(1,index=df.index)
    for i in range(1,len(df)):
        if df['Close'].iloc[i] <= lower.iloc[i-1]: direction.iloc[i]=1
        elif df['Close'].iloc[i] >= upper.iloc[i-1]: direction.iloc[i]=-1
        else: direction.iloc[i]=direction.iloc[i-1]
    return direction

def check_signal(stock_obj):
    sym=stock_obj['symbol']; token=stock_obj['token']
    try:
        to_date=datetime.now(); from_date=to_date - timedelta(days=5)
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")})['data']
        df=pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<20: return None

        df['EMA9']=df['Close'].ewm(span=9).mean()
        df['EMA15']=df['Close'].ewm(span=15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3
        df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff()
        gain=delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))
        df['MACD']=df['Close'].ewm(span=12).mean() - df['Close'].ewm(span=26).mean()
        df['DIR']=supertrend_dir(df,10,3)

        c1=df.iloc[-4]; c2=df.iloc[-3]; c4=df.iloc[-1]
        avg_vol=df['Volume'].iloc[-4:-1].mean()
        high_vol = c4['Volume'] > avg_vol * 1.3 # High Volume Condition

        # --- BUY: Notebook Pattern (C1 Green Big, C2 Red Small, C4 > C1 High Breakout) ---
        buy_pattern = (c1['Close']>c1['Open']) and (c2['Close']<c2['Open']) and (c4['Close']>c1['High']) and high_vol
        buy_cond = (c4['EMA9']>c4['VWAP']) and (c4['EMA15']>c4['VWAP']) and (df['DIR'].iloc[-1]<0) and (c4['RSI']>55) and (df['MACD'].iloc[-1]>0)

        # --- SELL: Notebook Pattern (C1 Red Big, C2 Green Small, C4 < C1 Low Breakdown) ---
        sell_pattern = (c1['Close']<c1['Open']) and (c2['Close']>c2['Open']) and (c4['Close']<c1['Low']) and high_vol
        sell_cond = (c4['EMA9']<c4['VWAP']) and (c4['EMA15']<c4['VWAP']) and (df['DIR'].iloc[-1]>0) and (c4['RSI']<45) and (df['MACD'].iloc[-1]<0)

        if buy_pattern and buy_cond:
            return ("BUY", f"🟢 BUY: {sym} @ {c4['Close']:.2f} ({stock_obj['pct']:+.2f}%) | C1H {c1['High']:.0f} Break")
        if sell_pattern and sell_cond:
            return ("SELL", f"🔴 SELL: {sym} @ {c4['Close']:.2f} ({stock_obj['pct']:+.2f}%) | C1L {c1['Low']:.0f} Break")
    except Exception as e:
        print(f"{sym} Error {e}")
    return None

gainer_results=[]; loser_results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    futures={ex.submit(check_signal, s): s for s in top10_gainers}
    for f in concurrent.futures.as_completed(futures):
        if f.result(): gainer_results.append(f.result())

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
    futures={ex.submit(check_signal, s): s for s in top10_losers}
    for f in concurrent.futures.as_completed(futures):
        if f.result(): loser_results.append(f.result())

all_res=gainer_results+loser_results
buy_done=[r[1] for r in all_res if r[0]=="BUY"]
sell_done=[r[1] for r in all_res if r[0]=="SELL"]
buy_from_gainer=[r[1] for r in gainer_results if r[0]=="BUY"]
sell_from_gainer=[r[1] for r in gainer_results if r[0]=="SELL"]
buy_from_loser=[r[1] for r in loser_results if r[0]=="BUY"]
sell_from_loser=[r[1] for r in loser_results if r[0]=="SELL"]

now=datetime.now().strftime("%d-%m-%Y %H:%M")
msg=f"⚡️ *1000Cr+ SCAN V6 - FINAL*\nTime: {now}\n"
msg+=f"\n*TOP 10 GAINERS (1000Cr+):*\n" + "\n".join([f"{x['symbol']} {x['pct']:+.2f}%" for x in top10_gainers])
msg+=f"\n\n*Signals from Gainers:*\n"
msg+=f"BUY ({len(buy_from_gainer)}): " + (", ".join(buy_from_gainer) if buy_from_gainer else "No BUY") + "\n"
msg+=f"SELL ({len(sell_from_gainer)}): " + (", ".join(sell_from_gainer) if sell_from_gainer else "No SELL")

msg+=f"\n\n*TOP 10 LOSERS (1000Cr+):*\n" + "\n".join([f"{x['symbol']} {x['pct']:+.2f}%" for x in top10_losers])
msg+=f"\n\n*Signals from Losers:*\n"
msg+=f"BUY ({len(buy_from_loser)}): " + (", ".join(buy_from_loser) if buy_from_loser else "No BUY") + "\n"
msg+=f"SELL ({len(sell_from_loser)}): " + (", ".join(sell_from_loser) if sell_from_loser else "No SELL")

msg+=f"\n\n✅ *TOTAL BUY DONE ({len(buy_done)}):*\n" + ("\n".join(buy_done) if buy_done else "No Buy Today")
msg+=f"\n\n❌ *TOTAL SELL DONE ({len(sell_done)}):*\n" + ("\n".join(sell_done) if sell_done else "No Sell Today")

print(msg)
send_tg(msg)
