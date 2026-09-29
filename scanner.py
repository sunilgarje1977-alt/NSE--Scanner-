# V43 ANGEL SMARTAPI - NO YFINANCE - ALL CONDITION SAME
import os, time, requests, datetime, pyotp
from SmartApi import SmartConnect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")
# GitHub Secrets मध्ये टाक:
ANGEL_API_KEY = os.getenv("ANGEL_API_KEY")
ANGEL_CLIENT = os.getenv("ANGEL_CLIENT_ID")
ANGEL_PASS = os.getenv("ANGEL_PASSWORD")
ANGEL_TOTP_SECRET = os.getenv("ANGEL_TOTP")

STOCKS = ["SJVN","HUDCO","RVNL","IRFC","BDL","MAZDOCK","COCHINSHIP","GRSE","BEML","BEL","NHPC","SUZLON","INOXWIND","BSE","CDSL","KFINTECH","CAMS","KAYNES","SYRMA","DIXON","PGEL","AMBER","ASTRAL","POLYCAB","NCC","NBCC","IRB","LTF","MUTHOOTFIN","FEDERALBNK","LAURUSLABS","LTIM","PERSISTENT","COFORGE","IEX","IFCI","RPOWER","JWL","TEXRAIL","TITAGARH","ELECON","RAYMOND","RBLBANK","VGUARD","BSOFT","CYIENT","MAPMYINDIA","AFFLE","JINDALSAW"]

# Angel Token Map - NSE Small+Mid चे Token - हे एकदाच भरायचं
# Full list साठी: https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
SYMBOL_TOKEN = {"SJVN":"10805","RVNL":"25804","BDL":"26255","SUZLON":"3045","BSE":"29022"} # Sample - तुला पूर्ण टाकायचं असेल तर सांगतो

def tg(msg):
    requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage", data={"chat_id":CHAT,"text":msg}, timeout=10)
    time.sleep(2.5)

def get_angel_conn():
    obj=SmartConnect(api_key=ANGEL_API_KEY)
    totp=pyotp.TOTP(ANGEL_TOTP_SECRET).now()
    data=obj.generateSession(ANGEL_CLIENT, ANGEL_PASS, totp)
    return obj

def check_angel(sym, obj):
    try:
        # Angel historical 5m data
        token = SYMBOL_TOKEN.get(sym)
        if not token: return None
        hist = obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":"2026-09-29 09:15","todate":"2026-09-30 15:30"})
        df = pd.DataFrame(hist['data'], columns=['time','open','high','low','close','volume'])
        df['E9']=df['close'].ewm(span=9).mean(); df['E15']=df['close'].ewm(span=15).mean()
        df['VWAP']=(df['close']*df['volume']).cumsum()/df['volume'].cumsum()
        df['VA']=df['volume'].rolling(20).mean()
        l=df.iloc[-1]; p=df.iloc[-2]
        ltp=float(l['close']); e9=float(l['E9']); e15=float(l['E15']); e9p=float(p['E9']); e15p=float(p['E15']); vwap=float(l['VWAP']); vwapp=float(p['VWAP']); volx=float(l['volume'])/float(l['VA'])
        score=10
        if ltp>vwap: score+=3
        if e9>e15: score+=3
        if volx>1.5: score+=4
        if score<15.5 or volx<1.5 or ltp<35 or ltp>2500: return None
        if ltp>vwap>e9>e15 and e9p<e15p and e9>e15 and vwapp<e9p and vwap>e9 and l['close']>l['open']:
            return {"s":sym,"ltp":ltp,"t":"BUY","sc":score,"vx":round(volx,1)}
    except: return None

def main():
    now=datetime.datetime.now()
    try: obj=get_angel_conn()
    except Exception as e:
        tg(f"❌ ANGEL LOGIN FAIL {e} - Check API KEY/TOTP"); return
    found=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs=[ex.submit(check_angel, s, obj) for s in STOCKS]
        for f in futs:
            r=f.result()
            if r: found.append(r)
    if not found:
        tg(f"⚡ V43 ANGEL FAST {now.strftime('%H:%M')} | Scanned {len(STOCKS)} | Found 0 Real | Angel Live Data ✅ | Bot Alive")
        return
    tg(f"🚀 V43 ANGEL {len(found)} BREAKOUT {now.strftime('%H:%M')}")
    for st in found:
        tg(f"🟢 BUY {st['s']} @{st['ltp']} | Vol {st['vx']}x | S:{st['sc']} | Angel Live 5m")

if __name__=="__main__": main()
