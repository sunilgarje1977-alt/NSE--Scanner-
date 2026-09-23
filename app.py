# app.py - 5M Momentum Blast Edition
import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="NSE Scanner Pro", layout="wide")

FNO_500 = ["BIKAJI.NS","RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS",
"ICICIBANK.NS","SBIN.NS","BHARTIARTL.NS","LT.NS","HAL.NS","BEL.NS",
"BSE.NS","ZOMATO.NS","POLYCAB.NS","RVNL.NS"] # पूर्ण 500 लिस्ट टाक

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_momentum_logic(df):
    if len(df) < 50: return False, {}
    df['EMA9'] = df['Close'].ewm(span=9).mean()
    df['EMA21'] = df['Close'].ewm(span=21).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['RSI'] = calculate_rsi(df['Close'])
    df['VOL_AVG20'] = df['Volume'].rolling(20).mean()
    last = df.iloc[-1]
    c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    
    cond_green = (c1['Close']>c1['Open'] and c2['Close']>c2['Open'] and 
                  c3['Close']>c3['Open'] and c2['Close']>c1['Close'] and 
                  c3['Close']>c2['Close'])
    cond_vol = last['Volume'] > 2 * last['VOL_AVG20']
    cond_ema = last['Close'] > last['EMA9'] > last['EMA21'] > last['EMA50']
    cond_rsi = 60 <= last['RSI'] <= 85
    prev10 = df.iloc[-13:-3]
    consol = ((prev10['High'].max()-prev10['Low'].min())/prev10['Low'].min()*100)
    
    all_ok = cond_green and cond_vol and cond_ema and cond_rsi and consol < 1.5
    info = {"price": round(last['Close'],2),
            "vol_mult": round(last['Volume']/last['VOL_AVG20'],2),
            "rsi": round(last['RSI'],2),
            "stoploss": round(c1['Low'],2),
            "target1": round(last['Close']*1.02,2),
            "target2": round(last['Close']*1.04,2)}
    return all_ok, info

st.title("🚀 NSE Scanner Pro - 5M Momentum Blast")
if st.button("💥 5M Momentum Blast", type="primary"):
    st.info("Scanning 500 stocks... 2-3 मिनिट लागेल")
    results = []
    for symbol in FNO_500:
        data = yf.download(symbol, period="5d", interval="5m", progress=False)
        if data.empty: continue
        if isinstance(data.columns, pd.MultiIndex): 
            data.columns = data.columns.get_level_values(0)
        ok, info = check_momentum_logic(data)
        if ok:
            results.append({"Symbol": symbol, **info})
    st.dataframe(pd.DataFrame(results))
