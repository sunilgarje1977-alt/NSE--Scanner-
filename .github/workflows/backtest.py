import requests, pyotp, os, concurrent.futures
from SmartApi import SmartConnect
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_token_map():
    d = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=15).json()
    mp={}
    for i in d:
        if i.get("exch_seg")=="NSE" and i.get("symbol"):
            sym=i["symbol"].replace("-EQ","").strip()
            if sym not in mp: mp[sym]=i["token"]
    return mp

TOKEN_MAP = get_token_map()

# तुझी 1000 LIST मधले TOP 100 घेऊन Backtest - FAST साठी
TEST_SYMBOLS = ["RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK","SBIN","BHARTIARTL","ITC","LT","KOTAKBANK","BAJFINANCE","AXISBANK","ASIANPAINT","MARUTI","TITAN","SUNPHARMA","ULTRACEMCO","NTPC","POWERGRID","ONGC","ADANIENT","ADANIPORTS","JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","BEL","HAL","BSE","MCX","TATAPOWER","TATAMOTORS","WIPRO","TECHM","HCLTECH","GRASIM","CIPLA","DIVISLAB","BRITANNIA","M&M","BAJAJ-AUTO","INDUSINDBK","SBILIFE","PFC","RECLTD","IREDA","RVNL","IRFC","IRCTC","BEML","BHEL","GAIL","VEDL","LICI","HINDZINC","JSWENERGY","COFORGE","PERSISTENT","MPHASIS","DIXON","KAYNES","POLYCAB","LTIM","BSOFT","APOLLOHOSP","MAXHEALTH","AUROPHARMA","LUPIN","GODREJPROP","DLF","PIDILITIND","SRF","MUTHOOTFIN","BANKBARODA","PNB","CANBK","AUBANK","FEDERALBNK","JIOFIN","ADANIPOWER","BALK RISIND".replace(" ",""),"HDFCBANK","ANANDRATHI","AHLUCONT","360ONE","SUZLON","ZOMATO","YESBANK","IEX","PAYTM","NYKAA","IDEA","RVNL","IRFC","NHPC","SJVN"]

def backtest_symbol(args):
    sym, obj, days = args
    token = TOKEN_MAP.get(sym)
    if not token: return None
    try:
        # 30 दिवसांचा data एका वेळी
        to_d = datetime.now()
        from_d = to_d - timedelta(days=days)
        from_str = from_d.strftime("%Y-%m-%d 09:15")
        to_str = to_d.strftime("%Y-%m-%d 15:30")
        data = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":from_str,"todate":to_str})
        if not data or "data" not in data or not data["data"]: return None
        df = pd.DataFrame(data["data"], columns=["ts","o","h","l","c","v"])
        if len(df) < 100: return None

        df["ema9"] = df["c"].ewm(span=9).mean()
        df["ema15"] = df["c"].ewm(span=15).mean()
        df["ema20"] = df["c"].ewm(span=20).mean()
        df["vwap"] = (df["c"]*df["v"]).cumsum()/df["v"].cumsum()
        delta = df["c"].diff()
        gain = delta.where(delta>0,0).rolling(14).mean()
        loss = -delta.where(delta<0,0).rolling(14).mean()
        df["rsi"] = 100 - (100/(1+gain/loss))
        df["macd"] = df["c"].ewm(span=12).mean() - df["c"].ewm(span=26).mean()
        df["macd_sig"] = df["macd"].ewm(span=9).mean()
        df["vol_avg"] = df["v"].rolling(20).mean()
        df["atr"] = (df["h"]-df["l"]).rolling(14).mean()

        trades=[]
        for i in range(30, len(df)-10): # प्रत्येक candle वर signal check
            last = df.iloc[i]; prev = df.iloc[i-1]
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
            if 40<=last["rsi"]<=70: buy+=1
            if 20<=last["rsi"]<=60: sell+=1
            if last["macd"]>last["macd_sig"]: buy+=1
            else: sell+=1
            if last["v"]>last["vol_avg"]*0.6: buy+=0.5; sell+=0.5

            ltp = float(last["c"]); atr = float(last["atr"]) if pd.notna(last["atr"]) else ltp*0.007
            # BUY Signal
            if buy>=5:
                entry = ltp; sl = min(df["l"].iloc[i-4:i+1].min(), ltp-atr*1.2)
                t1 = ltp+atr*1.5; t2 = ltp+atr*3; trail = sl
                # पुढचे 20 candle मध्ये result बघ
                highest = entry
                exit_price = None; status="OPEN"
                for j in range(i+1, min(i+20, len(df))):
                    future_ltp = float(df.iloc[j]["c"])
                    if future_ltp>highest: highest=future_ltp
                    if future_ltp>=t1 and trail<entry: trail=entry
                    if future_ltp>=t1:
                        nt = future_ltp - atr*1.2
                        if nt>trail: trail=nt
                    if future_ltp<=trail:
                        exit_price=trail; status="TRAIL" if trail>=entry else "SL"; break
                    if future_ltp>=t2: exit_price=t2; status="T2"; break
                if exit_price is None: # 3:15 close
                    exit_price = float(df.iloc[min(i+19, len(df)-1)]["c"]); status="EOD"
                pnl = exit_price - entry
                trades.append({"symbol":sym,"side":"BUY","entry":entry,"exit":exit_price,"pnl":pnl,"status":status})
            elif sell>=5:
                entry = ltp; sl = max(df["h"].iloc[i-4:i+1].max(), ltp+atr*1.2)
                t1 = ltp-atr*1.5; t2 = ltp-atr*3; trail = sl
                lowest = entry; exit_price=None; status="OPEN"
                for j in range(i+1, min(i+20, len(df))):
                    future_ltp = float(df.iloc[j]["c"])
                    if future_ltp<lowest: lowest=future_ltp
                    if future_ltp<=t1 and trail>entry: trail=entry
                    if future_ltp<=t1:
                        nt = future_ltp + atr*1.2
                        if nt<trail: trail=nt
                    if future_ltp>=trail:
                        exit_price=trail; status="TRAIL" if trail<=entry else "SL"; break
                    if future_ltp<=t2: exit_price=t2; status="T2"; break
                if exit_price is None:
                    exit_price = float(df.iloc[min(i+19, len(df)-1)]["c"]); status="EOD"
                pnl = entry - exit_price
                trades.append({"symbol":sym,"side":"SELL","entry":entry,"exit":exit_price,"pnl":pnl,"status":status})

        if not trades: return None
        total_pnl = sum([t["pnl"] for t in trades])
        win = len([t for t in trades if t["pnl"]>0]); loss = len([t for t in trades if t["pnl"]<=0])
        return {"symbol":sym,"trades":len(trades),"pnl":total_pnl,"win":win,"loss":loss,"winrate":win/len(trades)*100 if trades else 0,"details":trades[-3:]}
    except Exception as e:
        return None

# LOGIN
obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY","").strip())
obj.generateSession(os.getenv("ANGEL_CLIENT_ID","").strip(), os.getenv("ANGEL_PASSWORD","").strip(), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET","").strip()).now())

print("BACKTEST START - 30 DAYS")
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
    futs=[ex.submit(backtest_symbol,(s,obj,30)) for s in TEST_SYMBOLS]
    for f in concurrent.futures.as_completed(futs):
        r=f.result()
        if r: results.append(r)

results = sorted(results, key=lambda x: x["pnl"], reverse=True)

total_pnl = sum([r["pnl"] for r in results])
total_trades = sum([r["trades"] for r in results])
total_win = sum([r["win"] for r in results])
total_loss = sum([r["loss"] for r in results])

print("\n========== BACKTEST REPORT (30 DAYS) ==========")
print(f"Stocks Tested: {len(results)} | Total Trades: {total_trades}")
print(f"Total PnL: {total_pnl:.2f} | Win:{total_win} Loss:{total_loss} WinRate:{total_win/total_trades*100 if total_trades else 0:.1f}%")
print("-----------------------------------------------")
for r in results[:10]:
    print(f"{r['symbol']}: {r['trades']} Trades | PnL:{r['pnl']:.2f} | W:{r['win']} L:{r['loss']} WR:{r['winrate']:.1f}%")

print("\nTOP LOSER:")
for r in results[-5:]:
    print(f"{r['symbol']}: PnL:{r['pnl']:.2f} WR:{r['winrate']:.1f}%")

# Telegram ला पण पाठव
msg = f"📊 BACKTEST 30 DAYS | {len(results)} Stocks\n"
msg+=f"Total Trades: {total_trades} | PnL: {total_pnl:.2f}\n"
msg+=f"W:{total_win} L:{total_loss} WR:{total_win/total_trades*100 if total_trades else 0:.1f}%\n"
msg+="--------------------------------\nTOP 5:\n"
for r in results[:5]:
    msg+=f"{r['symbol']}: {r['pnl']:.1f} ({r['win']}/{r['trades']} WR:{r['winrate']:.0f}%)\n"

import requests
try:
    requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", data={"chat_id":os.getenv("TELEGRAM_CHAT_ID"),"text":msg}, timeout=10)
except: pass
