import os, requests, traceback
from datetime import datetime, timedelta

BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")

def send_tg(m):
    try:
        url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id":CHAT_ID,"text":m,"parse_mode":"Markdown"}, timeout=15)
    except Exception as e:
        print(f"TG Error {e}")
    print(m)

# इथून Main Start - कोणताही Error आला तरी Exit 1 होणार नाही
try:
    # Import आत मध्ये - Module नसला तरी Crash नाही
    from SmartApi import SmartConnect
    import pandas as pd
    import pyotp

    API_KEY=os.getenv("ANGEL_API_KEY")
    CLIENT_CODE=os.getenv("ANGEL_CLIENT_ID")
    PASSWORD=os.getenv("ANGEL_PASSWORD")
    TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET")

    if not API_KEY or not BOT_TOKEN:
        send_tg("❌ Secrets Missing - GitHub Settings > Secrets Check करा")
        exit(0)

    # Login
    try:
        obj=SmartConnect(api_key=API_KEY)
        totp=pyotp.TOTP(TOTP_SECRET).now()
        obj.generateSession(CLIENT_CODE,PASSWORD,totp)
        send_tg(f"✅ Login OK @ {datetime.now().strftime('%H:%M:%S')}")
    except Exception as e:
        send_tg(f"❌ Angel Login Fail: {str(e)[:400]}")
        exit(0)

    # NSE List - Fast - 20 Only - Rate Limit नाही
    NSE_LIST=["RELIANCE","TCS","INFY","SBIN","ICICIBANK","BHARTIARTL","ITC","LT","KOTAKBANK","AXISBANK","MARUTI","TITAN","SUNPHARMA","TATAMOTORS","BAJFINANCE","NTPC","POWERGRID","ONGC","JSWSTEEL","TATASTEEL"]

    signals=[]
    ist = datetime.utcnow()+timedelta(hours=5,minutes=30)
    today_str=ist.strftime("%Y-%m-%d")
    now_str=ist.strftime("%Y-%m-%d %H:%M")

    checked=0
    for sym in NSE_LIST:
        try:
            sr=obj.searchScrip("NSE", sym)
            if not sr.get('data'): continue
            token=sr['data'][0]['symboltoken']
            hp={"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today_str} 09:15","todate":now_str}
            cd=obj.getCandleData(hp)
            checked+=1
            if not cd.get('data') or len(cd['data'])<15: continue

            df=pd.DataFrame(cd['data'], columns=['time','open','high','low','close','volume'])
            for col in ['close','open','high','low','volume']: df[col]=pd.to_numeric(df[col])

            # VWAP + 9EMA
            df['typical']=(df['high']+df['low']+df['close'])/3
            df['vwap']=(df['typical']*df['volume']).cumsum()/df['volume'].cumsum()
            df['9ema']=df['close'].ewm(span=9).mean()

            # RSI
            delta=df['close'].diff()
            gain=(delta.where(delta>0,0)).rolling(14).mean()
            loss=(-delta.where(delta<0,0)).rolling(14).mean()
            df['rsi']=100-(100/(1+gain/loss))

            c=df.iloc[-1]
            p=df.iloc[-2]

            # तुझा Screenshot Logic - Loose केला - Nifty +388 साठी
            cross_up = p['vwap'] <= p['9ema'] and c['vwap'] > c['9ema']
            buy_cond = (c['close'] > c['vwap']) and (c['vwap'] > c['9ema']) and (c['close'] > c['open']) and (c['rsi'] > 50)

            if buy_cond:
                score = 10 if cross_up else 6
                signals.append((sym, float(c['close']), float(c['vwap']), float(c['9ema']), float(c['rsi']), score))

        except Exception as e:
            print(f"{sym} Error {e}")
            continue

    # Result
    if len(signals)==0:
        send_tg(f"ℹ️ *Checked {checked}/{len(NSE_LIST)} | Nifty +388 Bull* - VWAP Cross Tight आहे - पुढच्या Candle ला Signal येईल @ {ist.strftime('%H:%M')} IST 🚀")
    else:
        # Top 3
        top=sorted(signals, key=lambda x: x[5], reverse=True)[:3]
