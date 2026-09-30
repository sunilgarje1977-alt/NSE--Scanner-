import os, requests, pyotp, time
from SmartApi import SmartConnect
from datetime import datetime, timedelta
import pytz

# Secrets
API_KEY=os.getenv("ANGEL_API_KEY","").strip()
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID","").strip()
PASSWORD=os.getenv("ANGEL_PASSWORD","").strip()
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET","").strip()
BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID","").strip()

def send_tg(text):
    try:
        url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url,json={"chat_id":CHAT_ID,"text":text},timeout=15)
        print(text)
    except Exception as e:
        print(f"TG Error {e}")

def calc_ema(data, period):
    if len(data) < period: return None
    k = 2 / (period + 1)
    ema = sum(data[:period]) / period
    for p in data[period:]:
        ema = p * k + ema * (1 - k)
    return ema

def calc_rsi(closes, p=14):
    if len(closes) < p+1: return 50
    g=l=0
    for i in range(1,p+1):
        d=closes[-i]-closes[-i-1]
        if d>0: g+=d
        else: l-=d
    if l==0: return 75
    return 100-(100/(1+g/l if l!=0 else 9))

print("=== V51 TREND CATCHER START ===")
smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PASSWORD,pyotp.TOTP(TOTP_SECRET).now())
print("Login OK")

# IST TIME FIX - हे महत्वाचं
ist = pytz.timezone('Asia/Kolkata')
today = datetime.now(ist)
time_str = today.strftime('%d-%b %I:%M %p IST')

# SUNTV सारखे Trending Stocks
STOCKS=["SUNTV","UNIONBANK","PFC","RECLTD","NBCC","SUZLON","TATAPOWER","IRFC","SJVN","IDEA","MTNL"]

found=False

for sym in STOCKS:
    try:
        time.sleep(1)
        print(f"\nScanning {sym}...")
        search=smart.searchScrip("NSE",sym)
        if not search.get('data'): continue

        token=search['data'][0]['symboltoken']
        tradingsym=search['data'][0]['tradingsymbol']
        ltp=float(smart.ltpData("NSE",tradingsym,token)['data']['ltp'])

        # 5M Candle - तुझ्या Chart सारखं
        start=today.replace(hour=9,minute=15,second=0,microsecond=0)
        params={
            "exchange":"NSE",
            "symboltoken":token,
            "interval":"FIVE_MINUTE",
            "fromdate":start.strftime("%Y-%m-%d %H:%M"),
            "todate":today.strftime("%Y-%m-%d %H:%M")
        }
        candles=smart.getCandleData(params).get('data',[])
        if len(candles)<30:
            print(f"{sym} Less Candles")
            continue

        closes=[float(c[4]) for c in candles]
        volumes=[float(c[5]) for c in candles]

        ema9=calc_ema(closes,9)
        ema21=calc_ema(closes,21)
        ema50=calc_ema(closes,50)
        rsi=calc_rsi(closes)

        last_low=float(candles[-1][3])
        last_high=float(candles[-1][2])
        prev_high=float(candles[-2][2])

        avg_vol=sum(volumes[-10:])/10
        vol_spike=volumes[-1] > avg_vol*1.3

        trend_up = ltp > ema9 and ema9 > ema21 and ema21 > ema50

        print(f"{sym} LTP:{ltp} EMA9:{ema9:.1f} EMA21:{ema21:.1f} EMA50:{ema50:.1f} RSI:{rsi:.1f} VOL_SPIKE:{vol_spike}")

        # 1. CONFIRMED TREND BLAST - SUNTV सारखा
        if trend_up and 60 < rsi < 85 and vol_spike and ltp > prev_high:
            sl=ema9 if (ltp-ema9) < 3 else last_low
            risk=ltp-sl
            if risk < 0.2 or risk > 4: continue
            tgt1=ltp+risk
            tgt2=ltp+risk*2
            send_tg(
                f"🔥 TREND BLAST BUY {sym}\n"
                f"Time: {time_str}\n"
                f"LTP: {ltp:.2f}\n"
                f"RSI: {rsi:.1f} | VOL: {volumes[-1]/1000:.0f}K (Spike)\n"
                f"EMA: {ema9:.1f}>{ema21:.1f}>{ema50:.1f} ✅\n"
                f"---\n"
                f"SL: {sl:.2f} (9 EMA)\n"
                f"TSL: 9 EMA वर Trail करा\n"
                f"TARGET 1: {tgt1:.2f}\n"
                f"TARGET 2: {tgt2:.2f}\n"
                f"RR: 1:2\n"
                f"Chart सारखा Trend!"
            )
            found=True

        # 2. EARLY ALERT - Trend सुरू होण्याआधी
        elif ltp > ema9 and ema9 > ema21 and 58 < rsi < 70 and not vol_spike:
             send_tg(
                f"🟡 POTENTIAL {sym}\n"
                f"LTP: {ltp:.2f} RSI:{rsi:.1f}\n"
                f"EMA Cross होतोय, Watchlist मध्ये ठेवा!\n"
                f"Time: {time_str}"
             )

    except Exception as e:
        print(f"{sym} Error: {e}")

if not found:
    send_tg(f"V51 Live ✅ {time_str}\nNo Strong Trend Now\nFilter: Price>EMA9>21>50 + RSI 60-85 + Vol Spike + High Break\nScanned: {', '.join(STOCKS)}")

print("=== V51 DONE ===")
