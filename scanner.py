import os, pyotp, requests
from SmartApi import SmartConnect
from datetime import datetime, timedelta

REWARD_RATIO = 2.5
N_STOCKS = 1000 # किती स्कॅन करायचे - 1000

def send_telegram(msg):
    try:
        t=os.getenv("TELEGRAM_BOT_TOKEN"); c=os.getenv("TELEGRAM_CHAT_ID")
        requests.post(f"https://api.telegram.org/bot{t}/sendMessage", data={"chat_id":c,"text":msg,"parse_mode":"Markdown"}, timeout=15)
    except Exception as e:
        print(e)

try:
    print("LLOYDSENGG Pattern Scan Starting...")
    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET","").replace(" ","").strip()).now())

    # NSE 1000 Tokens Load
    master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=20).json()
    eq = [d for d in master if d['exch_seg']=='NSE' and d['symbol'].endswith('-EQ')][:N_STOCKS]
    print(f"Loaded {len(eq)} stocks")

    to_date=datetime.now()
    from_date=to_date-timedelta(days=3)
    matches=[]

    for d in eq:
        try:
            p={"exchange":"NSE","symboltoken":d['token'],"interval":"FIVE_MINUTE","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")}
            candles=obj.getCandleData(p).get('data',[])
            if len(candles)<40: continue

            # आजचे candles (शेवटचे 75 = 1 दिवस)
            today = candles[-75:]
            if len(today)<20: continue

            # LLOYDSENGG Logic
            open_range = today[:15] # 9:15-10:15
            or_high = max(c[2] for c in open_range)
            or_low = min(c[3] for c in open_range)

            curr = today[-1]
            prev = today[-2]

            # EMA 9,21,50 Simple Check (Close > MA)
            closes = [c[4] for c in today]
            ema9 = sum(closes[-9:])/9
            ema21 = sum(closes[-21:])/21

            vol_avg = sum(c[5] for c in today[-20:-1])/19

            cond1 = curr[4] > or_high # Opening Range Breakout
            cond2 = curr[4] > ema9 > ema21 # EMA वर
            cond3 = curr[5] > vol_avg*1.6 # Volume 1.6x
            cond4 = curr[4] > prev[4] # Green candle

            if cond1 and cond2 and cond3 and cond4:
                risk = curr[2]-curr[3]
                if risk==0: continue
                target = curr[4] + risk*REWARD_RATIO
                gain = round(((curr[4]-or_high)/or_high)*100,2)
                matches.append(f"*{d['symbol'].replace('-EQ','')}* ₹{curr[4]} | ORB:{or_high} | +{gain}% | SL:{round(curr[3],1)} T:{round(target,1)}")
        except:
            continue

    now=datetime.now().strftime('%d-%m %H:%M')
    if not matches:
        msg=f"📊 *NSE {N_STOCKS} LLOYDSENGG Pattern (1:{REWARD_RATIO})*\n⏰ {now}\n❌ 0 Match Found\n{len(eq)} Stocks स्कॅन - आज ORB Breakout नाही"
    else:
        msg=f"🚀 *LLOYDSENGG Type - {len(matches)} Found (1:{REWARD_RATIO})*\n⏰ {now}\n\n" + "\n\n".join(matches[:12])

    print(msg)
    send_telegram(msg)

except Exception as e:
    import traceback
    print(traceback.format_exc())
    send_telegram(f"Error: {e}")
