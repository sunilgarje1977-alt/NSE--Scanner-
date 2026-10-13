import os, requests, pyotp, pytz, sys
from datetime import datetime
from SmartApi import SmartConnect
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID=os.getenv("TELEGRAM_CHAT_ID")
API_KEY=os.getenv("ANGEL_API_KEY")
CLIENT_ID=os.getenv("ANGEL_CLIENT_ID")
PASSWORD=os.getenv("ANGEL_PASSWORD")
TOTP_SECRET=os.getenv("ANGEL_TOTP_SECRET")

def send_tele(msg):
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg, "parse_mode":"HTML"}, timeout=20)
    except: pass

ist=pytz.timezone('Asia/Kolkata')
now=datetime.now(ist)
today_str=now.strftime("%Y-%m-%d")

if now.weekday()>=5: sys.exit(0)
if now.hour<9 or (now.hour==9 and now.minute<15): sys.exit(0)
if now.hour>15 or (now.hour==15 and now.minute>35): print("Market Closed"); sys.exit(0)

smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID, PASSWORD, pyotp.TOTP(TOTP_SECRET).now())

master = requests.get("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json", timeout=30).json()

# STOCK LIST
tokens_all={}
for s in master:
    if s['exch_seg']=='NSE' and s['instrumenttype']=='' and s['symbol'].endswith('-EQ'):
        tokens_all[s['symbol'].replace('-EQ','')]=s['token']
stock_tokens=list(tokens_all.items())[:1000]

# TUESDAY WEEKLY EXPIRY
nifty_expiries=sorted(list(set([s['expiry'] for s in master if s['exch_seg']=='NFO' and s['name']=='NIFTY' and s['instrumenttype']=='OPTIDX'])))
weekly_expiry=""
for exp in nifty_expiries:
    try:
        if datetime.strptime(exp, "%d%b%Y").date() >= now.date():
            weekly_expiry=exp; break
    except: pass
if not weekly_expiry: weekly_expiry=nifty_expiries[0]

try: nifty_ltp=smart.ltpData("NSE", "NIFTY", "99926000")['data']['ltp']
except: nifty_ltp=25000
atm=round(nifty_ltp/50)*50
strikes=[atm-100, atm-50, atm, atm+50, atm+100]

nifty_opt_tokens=[]
for s in master:
    if s['exch_seg']=='NFO' and s['name']=='NIFTY' and s['expiry']==weekly_expiry and s['instrumenttype']=='OPTIDX':
        try:
            strike=int(float(s['strike'])/100)
            if strike in strikes:
                if 'CE' in s['symbol'][-5:]: otype='CE'
                elif 'PE' in s['symbol'][-5:]: otype='PE'
                else: continue
                nifty_opt_tokens.append((f"NIFTY {strike}{otype}", s['token'], strike, otype))
        except: pass
nifty_opt_tokens=list({x[0]:x for x in nifty_opt_tokens}.values())

print(f"V21 Scanning {len(stock_tokens)} Stocks + {len(nifty_opt_tokens)} Options | Exp {weekly_expiry}")

def get_indicators(df):
    df['EMA9']=df['C'].ewm(span=9).mean()
    df['VWAP']=(df['V']*(df['H']+df['L']+df['C'])/3).cumsum()/df['V'].cumsum()
    df['VOLAVG']=df['V'].rolling(20).mean()
    d=df['C'].diff()
    df['RSI']=100-(100/(1+d.where(d>0,0).rolling(14).mean()/-d.where(d<0,0).rolling(14).mean().replace(0,0.01)))
    return df

def scan_stock(item):
    name, token=item
    try:
        hist=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today_str} 09:15","todate":f"{today_str} 15:30"})
        if not hist or 'data' not in hist or len(hist['data'])<30: return None
        df=get_indicators(pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V']))
        curr=df.iloc[-1]; prev=df.iloc[-2]; first=df.iloc[0]
        pct=(curr['C']-first['O'])/first['O']*100
        vol=curr['V']/curr['VOLAVG'] if curr['VOLAVG']>0 else 0
        turnover=curr['V']*curr['C']
        if curr['C']<50 or turnover<1000000 or vol<1.5: return None

        cross_up=prev['EMA9']<prev['VWAP'] and curr['EMA9']>curr['VWAP']
        cross_down=prev['EMA9']>prev['VWAP'] and curr['EMA9']<curr['VWAP']

        # BUY
        if cross_up and curr['C']>curr['EMA9'] and 60<=curr['RSI']<=78:
            entry=curr['C']; sl=max(curr['EMA9']*0.998, curr['L']*0.998)
            if sl<entry*0.992: sl=entry*0.992
            risk=entry-sl
            if risk>0 and risk/entry<=0.01:
                return (vol, f"🟢 <b>{name} BUY @ {entry:.1f}</b> {pct:+.1f}% Vol:{vol:.1f}x RSI:{int(curr['RSI'])}\nSL:{sl:.1f} T1:{entry+risk*2.5:.1f}")

        # SELL
        if cross_down and curr['C']<curr['EMA9'] and 22<=curr['RSI']<=40:
            entry=curr['C']; sl=min(curr['EMA9']*1.002, curr['H']*1.002)
            if sl>entry*1.008: sl=entry*1.008
            risk=sl-entry
            if risk>0 and risk/entry<=0.01:
                return (vol, f"🔴 <b>{name} SELL @ {entry:.1f}</b> {pct:+.1f}% Vol:{vol:.1f}x RSI:{int(curr['RSI'])}\nSL:{sl:.1f} T1:{entry-risk*2.5:.1f}")
    except: return None

def scan_option(item):
    name, token, strike, otype=item
    try:
        hist=smart.getCandleData({"exchange":"NFO","symboltoken":token,"interval":"FIVE_MINUTE","fromdate":f"{today_str} 09:15","todate":f"{today_str} 15:30"})
        if not hist or 'data' not in hist or len(hist['data'])<30: return None
        df=get_indicators(pd.DataFrame(hist['data'], columns=['t','O','H','L','C','V']))
        curr=df.iloc[-1]; prev=df.iloc[-2]
        vol=curr['V']/curr['VOLAVG'] if curr['VOLAVG']>0 else 0
        if curr['C']<10 or vol<1.5: return None

        cross_up=prev['EMA9']<prev['VWAP'] and curr['EMA9']>curr['VWAP']
        cross_down=prev['EMA9']>prev['VWAP'] and curr['EMA9']<curr['VWAP']

        # CALL BUY - CE वर जातोय
        if otype=='CE' and cross_up and curr['C']>curr['EMA9'] and 60<=curr['RSI']<=78:
            entry=curr['C']; sl=curr['EMA9']*0.97
            return (vol+1, f"🟢 <b>{name} CALL BUY @ {entry:.1f}</b> Vol:{vol:.1f}x RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} T1:{entry*1.15:.1f} (15%) Exp:{weekly_expiry}")

        # PUT BUY - PE वर जातोय (Nifty खाली)
        if otype=='PE' and cross_up and curr['C']>curr['EMA9'] and 60<=curr['RSI']<=78:
            entry=curr['C']; sl=curr['EMA9']*0.97
            return (vol+1, f"🔴 <b>{name} PUT BUY @ {entry:.1f}</b> Vol:{vol:.1f}x RSI:{int(curr['RSI'])} {now.strftime('%H:%M')}\nSL:{sl:.1f} T1:{entry*1.15:.1f} (15%) Exp:{weekly_expiry}")

    except: return None

results=[]
with ThreadPoolExecutor(max_workers=40) as ex:
    futs={ex.submit(scan_stock,it):it for it in stock_tokens}
    futs.update({ex.submit(scan_option,it):it for it in nifty_opt_tokens})
    for f in as_completed(futs):
        r=f.result()
        if r: results.append(r)

if results:
    results_sorted=sorted(results, key=lambda x: x[0], reverse=True)
    texts=[x[1] for x in results_sorted]
    header=f"⚡️ <b>V21 BUY SELL CALL PUT {now.strftime('%H:%M')} Nifty:{nifty_ltp:.0f}</b>\nExp:{weekly_expiry} (Tuesday) | Vol 1.5x | RSI 60\n\n"
    send_tele(header + "\n\n".join(texts[:15]))
else:
    if now.minute<12:
        send_tele(f"⏳ {now.strftime('%H:%M')} No Setup Vol 1.5x - Nifty {nifty_ltp:.0f} ATM {atm} Exp {weekly_expiry}") 
