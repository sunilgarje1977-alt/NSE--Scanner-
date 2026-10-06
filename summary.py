import os, json, datetime, pytz
import pandas as pd
from SmartApi import SmartConnect

# --- API ---
API_KEY="YOUR_API_KEY"
CLIENT_ID="YOUR_CLIENT_ID"
PWD="YOUR_PWD"
TOTP_SECRET="YOUR_TOTP"
TELE_TOKEN="YOUR_TELE_TOKEN"
TELE_CHAT="YOUR_CHAT_ID"
STATE_FILE="state.json"

IST=pytz.timezone('Asia/Kolkata')
ist_now=lambda: datetime.datetime.now(IST)

smart=SmartConnect(api_key=API_KEY)
# ... (login code same as before) ...

def clean(df):
    df=df.rename(columns={"time":"Time"})
    return df

def get_nse_750():
    syms=["RELIANCE","TCS","INFY","HONASA","URBANCO","POLYCAB","DIXON","BSE","CDSL","HAL","BEL","BHEL","TATAMOTORS","TATASTEEL"]
    # तुझी जुनी 750 ची list इथे जशी होती तशीच राहू दे
    # जर token_map मधून घेत असशील तर खालची line वापर
    # syms.extend(list(token_map.keys()))
    return list(set(syms))[:80]

def analyze(sym, mode_hint=""):
    try:
        token=token_map.get(sym)
        if not token: return None
        fdate=(ist_now()-datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
        tdate=ist_now().strftime("%Y-%m-%d %H:%M")
        data=smart.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":fdate,"todate":tdate})
        if not data or 'data' not in data: return None
        df=pd.DataFrame(data['data'],columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<30: return None
        
        ltp=df['Close'].iloc[-1]
        c=df.iloc[-2] # previous candle for pattern
        df['EMA9']=df['Close'].ewm(9).mean()
        df['VWAP']=(df['High']+df['Low']+df['Close'])/3 * df['Volume']
        df['VWAP']=df['VWAP'].cumsum()/df['Volume'].cumsum()
        df['RSI']=100-(100/(1+df['Close'].diff().clip(lower=0).ewm(alpha=1/14).mean()/abs(df['Close'].diff().clip(upper=0)).ewm(alpha=1/14).mean()))
        
        # Pattern
        body=abs(c['Close']-c['Open'])+1
        low_p=min(c['Open'],c['Close'])-c['Low']
        up_p=c['High']-max(c['Open'],c['Close'])
        pat=""
        if low_p>body*1.5 and c['Close']>c['Open']: pat="HAMMER"
        if up_p>body*1.5 and c['Close']<c['Open']: pat="INV_HAMMER"

        # === नवीन Buy/Sell Score - 2 वर आणला ===
        buy_score=sum([
            df['Close'].iloc[-1]>df['EMA9'].iloc[-1],
            df['EMA9'].iloc[-1]>df['EMA9'].iloc[-2],
            df['RSI'].iloc[-1]>52,
            df['Close'].iloc[-1]>df['VWAP'].iloc[-1]
        ])
        sell_score=sum([
            df['Close'].iloc[-1]<df['EMA9'].iloc[-1],
            df['EMA9'].iloc[-1]<df['EMA9'].iloc[-2],
            df['RSI'].iloc[-1]<48,
            df['Close'].iloc[-1]<df['VWAP'].iloc[-1]
        ])

        if buy_score>=2:
            sl=ltp*0.985; tp=ltp*1.025
            return {"type":"BUY","symbol":sym,"score":buy_score,"pat":pat,"ltp":ltp,"sl":sl,"tp":tp,"volx":1.5}
        
        if sell_score>=2:
            sl=ltp*1.015; tp=ltp*0.975
            return {"type":"SELL","symbol":sym,"score":sell_score,"pat":pat,"ltp":ltp,"sl":sl,"tp":tp,"volx":1.5}

        return None
    except: return None

# State Management (तुझा जुना code same)
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f: st=json.load(f)
            if st['date']==ist_now().strftime("%Y-%m-%d"): return st
        except: pass
    return {"date":ist_now().strftime("%Y-%m-%d"),"active":[],"closed":[]}

state=load_state()
new_active=[]; trail_msg=""
# ... (trailing SL logic same as your old code) ...

# New Signal
universe=get_nse_750()
buys=[]; sells=[]
for sym in universe:
    if any(tr['symbol']==sym for tr in state['active']): continue
    res=analyze(sym)
    if res:
        if res['type']=="BUY": buys.append(res)
        else: sells.append(res)

# Telegram Send - फक्त Signal असेल तरच
if buys or sells:
    msg=""
    for b in buys: msg+=f"🟢 BUY {b['symbol']} @ {b['ltp']:.2f} SL {b['sl']:.2f} TGT {b['tp']:.2f} Score {b['score']}/4 {b['pat']}\n"
    for s in sells: msg+=f"🔴 SELL {s['symbol']} @ {s['ltp']:.2f} SL {s['sl']:.2f} TGT {s['tp']:.2f} Score {s['score']}/4 {s['pat']}\n"
    send_tg(msg)
