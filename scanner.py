import os, time, math, datetime
from SmartApi import SmartConnect
import pandas as pd

# --- CONFIG V4 - SUPER FILTER ---
CONFIG = {
    "TOTAL_STOCKS": 1000,
    "MAX_ACTIVE": 2,
    "MAX_DAILY": 6,
    "VOL_MULTIPLIER": 3.0,  # 3x Volume
    "RSI_BUY_MIN": 40, "RSI_BUY_MAX": 70,
    "RSI_SELL_MIN": 30, "RSI_SELL_MAX": 60,
    "TARGET_RATIO": 1.0, # 1:1 for High WinRate
    "T2_RATIO": 1.5,
    "T5_RATIO": 2.5
}

# Telegram
import requests
def send_tg(msg):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat, "text": msg, "parse_mode": "HTML"})

# Angel Login
api_key = os.getenv("ANGEL_API_KEY")
client_id = os.getenv("ANGEL_CLIENT_ID")
pwd = os.getenv("ANGEL_PASSWORD")
totp_secret = os.getenv("ANGEL_TOTP_SECRET")

obj = SmartConnect(api_key=api_key)
try:
    import pyotp
    totp = pyotp.TOTP(totp_secret).now()
    data = obj.generateSession(client_id, pwd, totp)
    print("LOGIN SUCCESS")
    send_tg(f"FAST BOT V4 STARTED - {CONFIG['TOTAL_STOCKS']} Stocks - {CONFIG['MAX_ACTIVE']} Active - {CONFIG['MAX_DAILY']} Daily - 1 Min - 1:1:5 Trail + 3xVol + RSI Filter")
except Exception as e:
    print(f"Login Failed {e}")
    exit()

# --- तुझा जुना 1000 Stocks चा Logic इथेच राहील ---
# फक्त BUY/SELL Condition मध्ये हे V4 Filter वापर:

def is_valid_signal(candle, rsi, vwap_status, vol_ratio, ema9, ema15, signal_type):
    if signal_type == "BUY":
        return (vol_ratio >= CONFIG["VOL_MULTIPLIER"] and 
                CONFIG["RSI_BUY_MIN"] < rsi < CONFIG["RSI_BUY_MAX"] and
                vwap_status == "UP" and ema9 > ema15 and
                candle['close'] > candle['open'])
    if signal_type == "SELL":
        return (vol_ratio >= CONFIG["VOL_MULTIPLIER"] and
                CONFIG["RSI_SELL_MIN"] < rsi < CONFIG["RSI_SELL_MAX"] and
                vwap_status == "DN" and ema9 < ema15 and
                candle['close'] < candle['open'])
    return False

# --- Main Loop (तुझा आधीचा Loop जसाच तसा) ---
# इथे तुझा while True वाला Scanner Loop असेल तोच ठेव
# फक्त SL/Target Calculation:
# SL = Candle High/Low
# T1 = Entry + (Entry-SL)*1.0
# T2 = Entry + (Entry-SL)*1.5
# T5 = Entry + (Entry-SL)*2.5
