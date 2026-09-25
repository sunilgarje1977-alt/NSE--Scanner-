import os, pyotp, requests
from SmartApi import SmartConnect
from datetime import datetime, timedelta

REWARD_RATIO = 2.5
N_STOCKS = 1000 # <-- इथे तू 1000 / 500 / 200 काहीही करू शकतो

def send_telegram(msg):
    try:
        t=os.getenv("TELEGRAM_BOT_TOKEN"); c=os.getenv("TELEGRAM_CHAT_ID")
        requests.post(f"https://api.telegram.org/bot{t}/sendMessage", data={"chat_id":c,"text":msg,"parse_mode":"Markdown"}, timeout=10)
    except: pass

try:
    obj = SmartConnect(api_key=os.getenv("ANGEL_API_KEY"))
    obj.generateSession(os.getenv("ANGEL_CLIENT_ID"), os.getenv("ANGEL_PASSWORD"), pyotp.TOTP(os.getenv("ANGEL_TOTP_SECRET","").replace(" ","").strip()).now())

    master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=20).json()
    eq = [d for d in master if d['exch_seg']=='NSE' and d['symbol'].endswith('-EQ')][:N_STOCKS]
    print(f"Scanning {len(eq)} stocks...")

    to_date=datetime.now(); from_date=to_date-timedelta(days=2)
    matches=[]
    for d in eq:
        try:
            p={"exchange":"NSE","symboltoken":d['token'],"interval":"FIVE_MINUTE","fromdate":from_date.strftime("%Y-%m-%d %H:%M"),"todate":to_date.strftime("%Y-%m-%d %H:%M")}
            data=obj.getCandleData(p).get('data',[])
            if len(data)<30: continue
            last20=data[-25:-5]; curr=data[-1]
            high20=max(c[2] for c in last20); vol_avg=sum(c[5] for c in last20)/len(last20)
            if (high20-min(c[3] for c in last20))/high20 <0.04 and curr[4]>high20 and curr[5]>vol_avg*1.5 and curr[4]>curr[1]:
                risk=curr[2]-curr[3]
                if risk>0:
                    target=curr[4]+risk*REWARD_RATIO
                    matches.append(f"{d['symbol'].replace('-EQ','')} ₹{curr[4]} T:{round(target,1)}")
        except: continue

    now=datetime.now().strftime('%d-%m %H:%M')
    if not matches:
        msg=f"📊 *NSE {N_STOCKS} WHIRLPOOL Scan (1:{REWARD_RATIO})*\n⏰ {now}\n❌ 0 Match Found\n{len(eq)} Stocks स्कॅन झाले - आज Pattern नाही"
    else:
        msg=f"🚀 *{len(matches)} Found - NSE {N_STOCKS} (1:{REWARD_RATIO})*\n⏰ {now}\n\n" + "\n".join(matches[:15])
    print(msg)
    send_telegram(msg)
except Exception as e:
    import traceback; print(traceback.format_exc())
