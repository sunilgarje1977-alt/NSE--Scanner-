import os, json, pyotp, urllib.request, pandas as pd, requests, time
from datetime import datetime
from SmartApi import SmartConnect

def clean(k): return os.getenv(k,"").strip().strip('"').strip("'")
API_KEY=clean('ANGEL_API_KEY'); CLIENT_ID=clean('ANGEL_CLIENT_ID'); PWD=clean('ANGEL_PASSWORD'); TOTP_SECRET=clean('ANGEL_TOTP_SECRET')
TELE_TOKEN=clean('TELEGRAM_BOT_TOKEN'); TELE_CHAT=clean('TELEGRAM_CHAT_ID')
smart=SmartConnect(api_key=API_KEY)
smart.generateSession(CLIENT_ID,PWD,pyotp.TOTP(TOTP_SECRET).now())

def send_tg(msg):
    try: requests.get(f"https://api.telegram.org/bot{TELE_TOKEN}/sendMessage", params={"chat_id":TELE_CHAT, "text":msg, "parse_mode":"Markdown"}, timeout=20)
    except: pass

if not os.path.exists("scrip_master.json"):
    urllib.request.urlretrieve("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json","scrip_master.json")
with open("scrip_master.json") as f: master=json.load(f)
token_map={s['name']:s['token'] for s in master if s['exch_seg']=='NSE' and s['symbol'].endswith('-EQ')}

# ===== NIFTY 750 UNIVERSE =====
def get_universe():
    try:
        n100=pd.read_csv("https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv")['Symbol'].tolist()
        n_mid=pd.read_csv("https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv")['Symbol'].tolist()
        n_small=pd.read_csv("https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap250list.csv")['Symbol'].tolist()
        # अजून 250 - Nifty Smallcap 50 + Microcap 200
        n_small2=pd.read_csv("https://www.niftyindices.com/IndexConstituent/ind_niftysmallcap50list.csv")['Symbol'].tolist()
        all_sym=list(set([s.strip().upper() for s in n100+n_mid+n_small+n_small2]))[:750]
        if len(all_sym)>400: return all_sym
    except: pass
    return list(token_map.keys())[:750]

UNIVERSE=get_universe()
print(f"Universe Loaded: {len(UNIVERSE)}")

def check_conditions(symbol):
    try:
        token=token_map.get(symbol)
        if not token: return None
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":(datetime.now()-pd.Timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),"todate":datetime.now().strftime("%Y-%m-%d %H:%M")})['data']
        df=pd.DataFrame(data, columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<50: return None

        # Indicators
        df['EMA9']=df['Close'].ewm(9).mean(); df['EMA15']=df['Close'].ewm(15).mean()
        df['TP']=(df['High']+df['Low']+df['Close'])/3; df['VWAP']=(df['TP']*df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff(); gain=delta.clip(lower=0).ewm(alpha=1/14).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss)); df['MACD']=df['Close'].ewm(12).mean()-df['Close'].ewm(26).mean()
        df['MACD_SIG']=df['Close'].ewm(26).mean()
        hl2=(df['High']+df['Low'])/2; tr=pd.concat([(df['High']-df['Low']),(df['High']-df['Close'].shift()).abs(),(df['Low']-df['Close'].shift()).abs()],axis=1).max(axis=1)
        atr=tr.rolling(10).mean(); lower=hl2-3*atr; upper=hl2+3*atr
        super_dir = 1 if df['Close'].iloc[-1]<=lower.iloc[-2] else -1 if df['Close'].iloc[-1]>=upper.iloc[-2] else 0

        c=df.iloc[-1]; c3=df.iloc[-4]; c3_high=df['High'].iloc[-4:-1].max(); c3_low=df['Low'].iloc[-4:-1].min()
        avg_vol=df['Volume'].iloc[-11:-1].mean(); vol_spike=c['Volume']>avg_vol*1.2

        # ===== BUY CONDITIONS (7) =====
        buy_cond=[
            c['Close']>c3_high, # 1. THREE CANDLE BREAKOUT
            c['EMA9']>c['VWAP'], # 2
            c['EMA15']>c['VWAP'], # 3
            super_dir<0, # 4 Supertrend Bullish
            c['RSI']>55 and c['RSI']<75, # 5
            df['MACD'].iloc[-1]>0, # 6
            vol_spike # 7
        ]
        sell_cond=[
            c['Close']<c3_low, # 1. THREE CANDLE BREAKDOWN
            c['EMA9']<c['VWAP'], # 2
            c['EMA15']<c['VWAP'], # 3
            super_dir>0, # 4 Supertrend Bearish
            c['RSI']<45 and c['RSI']>25, # 5
            df['MACD'].iloc[-1]<0, # 6
            vol_spike # 7
        ]
        b_score=sum(buy_cond); s_score=sum(sell_cond)
        ltp=c['Close']; atr_val=atr.iloc[-1]

        if b_score>=5:
            sl=min(c3_low, ltp-atr_val*1.5); risk=ltp-sl
            tgt1=ltp+risk*2; tgt2=ltp+risk*5 # 1:2 and 1:5
            return {"type":"BUY","sym":symbol,"score":b_score,"ltp":ltp,"sl":sl,"tgt1":tgt1,"tgt2":tgt2,"risk":risk}
        if s_score>=5:
            sl=max(c3_high, ltp+atr_val*1.5); risk=sl-ltp
            tgt1=ltp-risk*2; tgt2=ltp-risk*5
            return {"type":"SELL","sym":symbol,"score":s_score,"ltp":ltp,"sl":sl,"tgt1":tgt1,"tgt2":tgt2,"risk":risk}
        return None
    except Exception as e:
        return None

# ===== MAIN - TOP GAINERS / LOSERS =====
def get_perc(sym):
    try:
        d=smart.ltpData("NSE", sym+"-EQ", token_map.get(sym))
        ltp=d['data']['ltp']; close=d['data']['close']
        return (ltp-close)/close*100 if close else 0
    except: return 0

print("Finding Top Gainers/Losers in 750...")
perc_list=[]
for sym in UNIVERSE[:250]: # API limit save - 250 मध्ये Top काढतो, रोज Rotate होईल
    perc_list.append((sym,get_perc(sym)))
    time.sleep(0.15)

perc_list.sort(key=lambda x: x[1], reverse=True)
top_gainers=[x[0] for x in perc_list[:20]] # Large+Mid+Small मधले Top 20 Gainers
top_losers=[x[0] for x in perc_list[-20:]] # Top 20 Losers

all_check=top_gainers+top_losers
buy_list=[]; sell_list=[]

for sym in all_check:
    res=check_conditions(sym)
    if res:
        if res['type']=='BUY' and len(buy_list)<10: buy_list.append(res)
        if res['type']=='SELL' and len(sell_list)<10: sell_list.append(res)
    time.sleep(0.3)
    if len(buy_list)>=10 and len(sell_list)>=10: break

# ===== TELEGRAM MESSAGE =====
msg=f"📊 *NSE 750 | Large+Mid+Small Top Gainers/Losers*\n_Time: {datetime.now().strftime('%d-%m %H:%M')}_\n\n"

if buy_list:
    msg+=f"🟢 *BUY - {len(buy_list)} SIGNALS (3 Candle + 5/7 Cond)*\n"
    for r in buy_list:
        msg+=f"\nBUY {r['sym']} {r['score']}/7\nEntry: {r['ltp']:.1f} | SL: {r['sl']:.1f}\nTGT1(1:2): {r['tgt1']:.1f} [50% Book]\nTGT2(1:5): {r['tgt2']:.1f} [50% Trail SL to Cost]\n"
else:
    msg+=f"\n🟢 BUY - No Match Today\n"

if sell_list:
    msg+=f"\n🔴 *SELL - {len(sell_list)} SIGNALS*\n"
    for r in sell_list:
        msg+=f"\nSELL {r['sym']} {r['score']}/7\nEntry: {r['ltp']:.1f} | SL: {r['sl']:.1f}\nTGT1(1:2): {r['tgt1']:.1f} [50% Book]\nTGT2(1:5): {r['tgt2']:.1f} [50% Trail]\n"
else:
    msg+=f"\n🔴 SELL - No Match Today\n"

msg+=f"\n_Strategy: 3 Candle BO/BD + EMA9/15>VWAP + Supertrend + RSI + MACD + Volume_"

print(msg)
send_tg(msg)
