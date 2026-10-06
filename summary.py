import os, json, datetime, pytz
import pandas as pd
from SmartApi import SmartConnect

API_KEY="YOUR_API_KEY"
CLIENT_ID="YOUR_CLIENT_ID"
PWD="YOUR_PWD"
TOTP_SECRET="YOUR_TOTP"
TELE_TOKEN="YOUR_TELE_TOKEN"
TELE_CHAT="YOUR_CHAT_ID"
STATE_FILE="state.json"

IST=pytz.timezone('Asia/Kolkata')
def ist_now():
    return datetime.datetime.now(IST)

smart=SmartConnect(api_key=API_KEY)

def get_nse_750():
    syms=["RELIANCE","TCS","INFY","HONASA","URBANCO"]
    return syms

def analyze(sym, mode_hint=""):
    try:
        token=token_map.get(sym)
        if not token:
            return None
        fdate=(ist_now()-datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
        tdate=ist_now().strftime("%Y-%m-%d %H:%M")
        req={"exchange":"NSE","symboltoken":token,"interval":"FIFTEEN_MINUTE","fromdate":fdate,"todate":tdate}
        data=smart.getCandleData(req)
        if not data or 'data' not in data:
            return None
        df=pd.DataFrame(data['data'],columns=['Time','Open','High','Low','Close','Volume'])
        if len(df)<30:
            return None
        
        ltp=df['Close'].iloc[-1]
        c=df.iloc[-2]
        df['EMA9']=df['Close'].ewm(9).mean()
        df['VWAP']=((df['High']+df['Low']+df['Close'])/3 * df['Volume']).cumsum()/df['Volume'].cumsum()
        delta=df['Close'].diff()
        gain=delta.clip(lower=0).ewm(alpha=1/14).mean()
        loss=abs(delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI']=100-(100/(1+gain/loss))

        body=abs(c['Close']-c['Open'])+1
        low_p=min(c['Open'],c['Close'])-c['Low']
        up_p=c['High']-max(c['Open'],c['Close'])
        pat=""
        if low_p>body*1.5 and c['Close']>c['Open']:
            pat="HAMMER"
        if up_p>body*1.5 and c['Close']<c['Open']:
            pat="INV_HAMMER"

        buy_score=0
        if df['Close'].iloc[-1]>df['EMA9'].iloc[-1]:
            buy_score+=1
        if df['EMA9'].iloc[-1]>df['EMA9'].iloc[-2]:
            buy_score+=1
        if df['RSI'].iloc[-1]>52:
            buy_score+=1
        if df['Close'].iloc[-1]>df['VWAP'].iloc[-1]:
            buy_score+=1

        sell_score=0
        if df['Close'].iloc[-1]<df['EMA9'].iloc[-1]:
            sell_score+=1
        if df['EMA9'].iloc[-1]<df['EMA9'].iloc[-2]:
            sell_score+=1
        if df['RSI'].iloc[-1]<48:
            sell_score+=1
        if df['Close'].iloc[-1]<df['VWAP'].iloc[-1]:
            sell_score+=1

        if buy_score>=2:
            sl=ltp*0.985
            tp=ltp*1.025
            return {"type":"BUY","symbol":sym,"score":buy_score,"pat":pat,"ltp":ltp,"sl":sl,"tp":tp}

        if sell_score>=2:
            sl=ltp*1.015
            tp=ltp*0.975
            return {"type":"SELL","symbol":sym,"score":sell_score,"pat":pat,"ltp":ltp,"sl":sl,"tp":tp}

        return None
    except:
        return None

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                st=json.load(f)
                if st['date']==ist_now().strftime("%Y-%m-%d"):
                    return st
        except:
            pass
    return {"date":ist_now().strftime("%Y-%m-%d"),"active":[],"closed":[]}

state=load_state()
universe=get_nse_750()
buys=[]
sells=[]
for sym in universe:
    if any(tr["symbol"]==sym for tr in state["active"]):
        continue
    res=analyze(sym)
    if res:
        if res["type"]=="BUY":
            buys.append(res)
        else:
            sells.append(res)
