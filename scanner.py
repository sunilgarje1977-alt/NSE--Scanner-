import os, requests, pyotp, time
from SmartApi import SmartConnect
from datetime import datetime

API_KEY=os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD=os.getenv("ANGEL_PASSWORD","").strip()
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET","").strip()
BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","").strip()

def send_tg(text):
    try:
        url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url,json={"chat_id":CHAT_ID,"text":text},timeout=10)
        print(text)
    except Exception as e:
        print(e)

def calc_ema(data, period):
    if len(data) < period: return None
    k = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for price in data[period:]:
        ema = price * k + ema * (1 - k)
    return ema

def calc_rsi(closes, p=14):
    if len(closes)<p+1: return 50
    g=l=0
    for i in range(1,p+1):
        d=closes[-i]-closes[-i-1]
        if d>0: g+=d
        else: l-=d
    if l==0: return 80
    rs=g/l if l!=0 else 10
    return 100-(100/(1+rs))

print("V50 TREND CATCHER START")
smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PASSWORD,pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

today=datetime.now()
# SUNTV सारखे Stocks - जे Trend करतात
STOCKS=["SUNTV","UNIONBANK","PFC","RECLTD","NBCC","SUZLON","TATAPOWER","IRFC","SJVN","IDEA"]
found=False

for sym in STOCKS:
    try:
        time.sleep(1.2)
        s=smart.searchScrip("NSE",sym)
        if not s['data']: continue
        token=s['data'][0]['symboltoken']
        ts=s['data'][0]['tradingsymbol']
        ltp=float(smart.ltpData("NSE",ts,token)['data']['ltp'])

        start=today.replace(hour=9,minute=15,second=0,microsecond=0)
        params={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":start.strftime("%Y-%m-%d %H:%M"),"todate":today.strftime("%Y-%m-%d %H:%M")}
        candles=smart.getCandleData(params).get('data',[])
        if len(candles)<25: continue

        closes=[float(c[4]) for c in candles]
        volumes=[float(c[5]) for c in candles]

        ema9=calc_ema(closes,9)
        ema21=calc_ema(closes,21)
        ema50=calc_ema(closes,50)
        rsi=calc_rsi(closes)

        if not ema9 or not ema21 or not ema50: continue

        last_low=float(candles[-1][3])
        last_high=float(candles[-1][2])
        avg_vol=sum(volumes[-10:-1])/9 if len(volumes)>10 else volumes[-1]
        vol_spike = volumes[-1] > avg_vol*1.5

        # TREND CATCH LOGIC - SUNTV सारखा
        # 1. Price > EMA9 > EMA21 > EMA50
        # 2. RSI 65-85 (Strong but not overbought >90)
        # 3. Volume Spike
        trend_up = ltp > ema9 > ema21 > ema50
        trend_down = ltp < ema9 < ema21 < ema50

        print(f"{sym} LTP:{ltp} EMA9:{ema9:.1f} EMA21:{ema21:.1f} EMA50:{ema50:.1f} RSI:{rsi:.1f} TREND:{trend_up} VOL:{vol_spike}")

        if trend_up and rsi > 65 and rsi < 88 and vol_spike:
            sl=ema9 # SL = 9 EMA
            if ltp - sl < 0.5: sl = last_low # जर SL जवळ असेल तर Candle Low
            risk=ltp-sl
            tgt=ltp+ (risk*2) # RR 1:2 for Trend
            send_tg(f"🔥 TREND BLAST BUY {sym}\nLTP: {ltp:.2f} (+Trend)\nRSI: {rsi:.1f} | VOL: Spike ✅\nEMA: {ema9:.1f}>{ema21:.1f}>{ema50:.1f} ✅\nSL: {sl:.2f} (9 EMA)\nTSL: {ema9:.2f} -> Trail with 9 EMA\nTARGET 1: {tgt*0.5 + ltp*0.5:.2f} | TARGET 2: {tgt:.2f}\nRR: 1:2\nChart सारखा Trend Catch!")
            found=True

        elif trend_down and rsi < 40:
            sl=ema9
            risk=sl-ltp
            tgt=ltp-risk*2
            send_tg(f"🔻 TREND BREAK SELL {sym}\nLTP:{ltp:.2f}\nRSI:{rsi:.1f}\nEMA: {ema9:.1f}<{ema21:.1f}<{ema50:.1f}\nSL:{sl:.2f}\nTARGET:{tgt:.2f}")

    except Exception as e:
        print(f"{sym} Err {e}")

if not found:
    send_tg(f"V50 Trend Scanner Live - {today.strftime('%H:%M')}\nNo Strong Trend Now\nFilter: Price>EMA9>EMA21>EMA50 + RSI>65 + Vol Spike\nScanned: SUNTV, UNIONBANK etc.")

print("V50 DONE")
