import os, requests, pandas as pd
from SmartApi import SmartConnect
import pyotp
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import pytz

def clean(s): return os.getenv(s,"").strip()
def send_tg(m):
    try:
        requests.post(f"https://api.telegram.org/bot{clean('TELEGRAM_BOT_TOKEN')}/sendMessage",
        json={"chat_id": clean('TELEGRAM_CHAT_ID'), "text": m, "parse_mode":"Markdown"}, timeout=15)
    except: pass

# Angel Login
obj=SmartConnect(api_key=clean("ANGEL_API_KEY"))
obj.generateSession(clean("ANGEL_CLIENT_ID"), clean("ANGEL_PASSWORD"), pyotp.TOTP(clean("ANGEL_TOTP_SECRET")).now())

inst=pd.read_json("https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json")
nse=inst[(inst['exch_seg']=='NSE') & (inst['instrumenttype'].isin(['EQ']))]
TOP_10 = ["ULTRAMAR", "TEXRAIL", "CEWATER", "AEGISVOPAK", "PREMIERPOL", "KLBRENG-B", "SANGAMIND", "SHANTIGEAR", "XTRANET", "MOBIKWIK"]
tokens=nse[['token','symbol']].values.tolist()

def calc_rsi(s, p=14):
    d=s.diff(); g=d.where(d>0,0).rolling(p).mean(); l=-d.where(d<0,0).rolling(p).mean()
    rs=g/l; return 100-(100/(1+rs))
def calc_vwap(df): return (df['c']*df['v']).cumsum()/df['v'].cumsum()

def is_marubozu_bull(c):
    body=abs(c['c']-c['o']); rng=c['h']-c['l']; uw=c['h']-max(c['c'],c['o']); lw=min(c['c'],c['o'])-c['l']
    return c['c']>c['o'] and body>=rng*0.7 and uw<body*0.25 and lw<body*0.25
def is_marubozu_bear(c):
    body=abs(c['c']-c['o']); rng=c['h']-c['l']; uw=c['h']-max(c['c'],c['o']); lw=min(c['c'],c['o'])-c['l']
    return c['c']<c['o'] and body>=rng*0.7 and uw<body*0.25 and lw<body*0.25
def is_engulf_bull(p,c): return p['c']<p['o'] and c['c']>c['o'] and c['c']>p['o'] and c['o']<p['c']
def is_engulf_bear(p,c): return p['c']>p['o'] and c['c']<c['o'] and c['c']<p['o'] and c['o']>p['c']
def is_hammer(c):
    body=abs(c['c']-c['o']); uw=c['h']-max(c['c'],c['o']); lw=min(c['c'],c['o'])-c['l']
    return body>0 and lw>=body*2 and uw<body*0.4 and c['c']>c['o']
def is_shooting(c):
    body=abs(c['c']-c['o']); uw=c['h']-max(c['c'],c['o']); lw=min(c['c'],c['o'])-c['l']
    return body>0 and uw>=body*2 and lw<body*0.4 and c['c']<c['o']

def scan_one(item):
    token,sym=item
    try:
        data=obj.getCandleData({"exchange":"NSE","symboltoken":token,"interval":"FIVE_MINUTE","fromdate": datetime.now().strftime("%Y-%m-%d 09:15"), "todate": datetime.now().strftime("%Y-%m-%d %H:%M")})
        if not data or 'data' not in data: return None
        df=pd.DataFrame(data['data'], columns=['t','o','h','l','c','v'])
        if
