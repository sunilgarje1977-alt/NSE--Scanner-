import requests, pyotp, os, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd, numpy as np
from datetime import datetime, timedelta

def get_token_map():
    d = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=15).json()
    return {i["symbol"].replace("-EQ",""): i["token"] for i in d if i.get("exch_seg")=="NSE" and i.get("symbol")}

TOKEN_MAP = get_token_map()
TEST = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","JSWSTEEL","TATASTEEL","BEL","HAL","BSE","MCX","TATAPOWER","WIPRO","TECHM","HCLTECH","CIPLA","DIVISLAB","M&M","BAJAJ-AUTO","SBILIFE","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BHEL","GAIL","VEDL","LICI","JSWENERGY","COFORGE","PERSISTENT","DIXON","POLYCAB","LTIM","BSOFT","APOLLOHOSP","MAXHEALTH","DLF","PIDILITIND","SRF","BANKBARODA","PNB","CANBK","AUBANK","FEDERALBNK","JIOFIN","ADANIPOWER","BALK RISIND".replace(" ",""),"360ONE","SUZLON","ZOMATO","YESBANK","IEX","PAYTM","IDEA","ANANDRATHI","AHLUCONT"]

def backtest_sym(args):
    sym, obj = args
    token = TOKEN_MAP.get(sym)
    if not token: return None
    try:
        total_trades=[];
        # 60 दिवस - दिवस-वार Backtest
        for day_offset in range(1,61):
            dt = datetime.now() - timedelta(days=day_offset)
            if dt.weekday()>=5: continue
            from_str = dt.strftime("%Y-%m-%d 09:15")
            to_str = dt.strftime("%Y-%m-%d 15:30")
            data = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_str,"todate":to_str})
            if not data or "data" not in data or not data["data"] or len(data["data"])<50: continue
            df = pd.DataFrame(data["data"], columns=["ts","o","h","l","c","v"])
            df["ema9"]=df["c"].ewm(9).mean(); df["ema15"]=df["c"].ewm(15).mean(); df["ema20"]=df["c"].ewm(20).mean()
            df["vwap"]=(df["c"]*df["v"]).cumsum()/df["v"].cumsum()
            delta=df["c"].diff(); gain=delta.where(delta>0,0).rolling(14).mean(); loss=-delta.where(delta<0,0).rolling(14).mean()
            df["rsi"]=100-(100/(1+gain/loss)); df["macd"]=df["c"].ewm(12).mean()-df["c"].ewm(26).mean(); df["macd_sig"]=df["macd"].ewm(9).mean()
            df["vol_avg"]=df["v"].rolling(20).mean(); df["atr"]=(df["h"]-df["l"]).rolling(14).mean()
            # 1 दिवसात max 1 trade
            traded=False
            for i in range(30, len(df)-5):
                if traded: break
                last=df.iloc[i]; prev=df.iloc[i-1]
                if pd.isna(last["rsi"]) or pd.isna(last["atr"]): continue
                buy=0; sell=0
                if last["c"]>last["o"] and prev["c"]<prev["o"]: buy+=1
                if last["c"]<last["o"] and prev["c"]>prev["o"]: sell+=1
                if prev["ema9"]<prev["ema15"] and last["ema9"]>last["ema15"]: buy+=1
                if prev["ema9"]>prev["ema15"] and last["ema9"]<last["ema15"]: sell+=1
                if df["c"].iloc[i-2:i+1].is_monotonic_increasing: buy+=1
                if df["c"].iloc[i-2:i+1].is_monotonic_decreasing: sell+=1
                if last["ema9"]>last["vwap"]: buy+=1
                else: sell+=1
                if last["c"]>last["ema20"]: buy+=1
                else: sell+=1
                if 45<=last["rsi"]<=68: buy+=1 # TIGHT RSI FILTER
                if 32<=last["rsi"]<=58: sell+=1
                if last["macd"]>last["macd_sig"]: buy+=1
                else: sell+=1
                if last["v"]>last["vol_avg"]*1.2: buy+=0.5; sell+=0.5 # Volume 1.2x पाहिजे

                ltp=float(last["c"]); atr=float(last["atr"]) if pd.notna(last["atr"]) else ltp*0.01
                # SCORE 6/8 पाहिजे - आधी 4.5 होता म्हणून Loss जास्त!
                if buy>=6 and not traded:
                    entry=ltp; sl=ltp-atr*1.8; t1=ltp+atr*1.5; t2=ltp+atr*3
                    # Exit simulation
                    exit_price=None; pnl=0
                    for j in range(i+1, len(df)):
                        cur=df.iloc[j]
                        if cur["l"]<=sl: exit_price=sl; pnl=sl-entry; break
                        if cur["h"]>=t2: exit_price=t2; pnl=t2-entry; break
                        if cur["h"]>=t1 and j>i+3: # T1 नंतर 15 min थांबून Trail
                            if cur["c"]<cur["c"]-atr: exit_price=cur["c"]; pnl=cur["c"]-entry; break
                    if exit_price is None: exit_price=float(df.iloc[-1]["c"]); pnl=exit_price-entry
                    total_trades.append({"pnl":pnl,"r":pnl/(entry-sl) if entry!=sl else 0})
                    traded=True
                elif sell>=6 and not traded:
                    entry=ltp; sl=ltp+atr*1.8; t1=ltp-atr*1.5; t2=ltp-atr*3
                    exit_price=None
                    for j in range(i+1, len(df)):
                        cur=df.iloc[j]
                        if cur["h"]>=sl: exit_price=sl; pnl=entry-sl; break
                        if cur["l"]<=t2: exit_price=t2; pnl=entry-t2; break
                        if cur["l"]<=t1 and j>i+3:
                            if cur["c"]>cur["c"]+atr: exit_price=cur["c"]; pnl=entry-cur["c"]; break
                    if exit_price is None: exit_price=float(df.iloc[-1]["c"]); pnl=entry-exit_price
                    total_trades.append({"pnl":pnl,"r":pnl/(sl-entry) if sl!=entry else 0})
                    traded=True
        if not total_trades: return None
        win=len([t for t in total_trades if t["pnl"]>0]); loss=len(total_trades)-win
        avg_r=np.mean([t["r"] for t in total_trades])
        total_pnl=sum([t["pnl"] for t in total_trades])
        return {"sym":sym,"trades":len(total_trades),"win":win,"loss":loss,"wr":win/len(total_trades)*100,"avgR":avg_r,"pnl":total_pnl}
    except: return None

obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY","").strip())
obj.generateSession(os.getenv("ANGEL_CLIENT_ID","").strip(), os.getenv("ANGEL_PASSWORD","").strip(), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET","").strip()).now())

results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
    futs=[ex.submit(backtest_sym,(s,obj)) for s in TEST]
    for f in concurrent.futures.as_completed(futs):
        r=f.result()
        if r: results.append(r)

results=sorted(results, key=lambda x: x["avgR"], reverse=True)
total_trades=sum([r["trades"] for r in results]); total_win=sum([r["win"] for r in results]); total_loss=sum([r["loss"] for r in results])
avgR=np.mean([r["avgR"] for r in results]) if results else 0
wr=total_win/total_trades*100 if total_trades else 0

msg=f"📊 60 DAYS BACKTEST - IMPROVED (6/8 Score)\n"
msg+=f"Total Trades: {total_trades}\n"
msg+=f"Win: {total_win} Loss: {total_loss}\n"
msg+=f"Winrate: {wr:.1f}%\n"
msg+=f"Avg: {avgR:.2f}R\n"
msg+=f"Top: {', '.join([r['sym']+':'+str(r['trades']) for r in results[:3]])}\n"
msg+="---\nBest 5:\n"
for r in results[:5]: msg+=f"{r['sym']} WR:{r['wr']:.0f}% AvgR:{r['avgR']:.2f}R Trades:{r['trades']}\n"

print(msg)
import requests
try: requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", data={"chat_id":os.getenv("TELEGRAM_CHAT_ID"),"text":msg}, timeout=10)
except: pass
