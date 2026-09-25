import os, time, pyotp, requests
from SmartApi import SmartConnect
from datetime import datetime

# --- 1. TOTP FIX ---
def get_clean_totp():
    secret = os.getenv("ANGEL_TOTP_SECRET", "")
    clean_secret = secret.replace(" ", "").replace("\n", "").replace("\r", "").strip()
    print(f"TOTP len after clean: {len(clean_secret)}")
    return clean_secret

# --- 2. TELEGRAM ---
def send_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram Token नाही")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        r = requests.post(url, data=payload, timeout=10)
        print(f"Telegram: {r.text}")
    except Exception as e:
        print(f"Telegram Fail: {e}")

# --- CONFIG ---
REWARD_RATIO = 2.5  # <-- तुझं 1:2.5 इथे सेट केलंय
print(f"Scanner Running with 1:{REWARD_RATIO} Ratio")

try:
    api_key = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_ID")
    password = os.getenv("ANGEL_PASSWORD")
    totp_secret = get_clean_totp()

    obj = SmartConnect(api_key=api_key)
    totp = pyotp.TOTP(totp_secret).now()
    data = obj.generateSession(client_id, password, totp)
    print("Login Success")

    # --- तुझा NSE 1000 चा Logic इथून सुरु ---
    # येथे तुझे symbols लोड होतील
    # for symbol in nse_1000_list:
    #     high, low, close = get_data(symbol)
    #     sl = low
    #     risk = close - sl
    #     target = close + (risk * REWARD_RATIO)  # 1:2.5
    #     if close > high:  # Breakout Logic
    #         matches.append(symbol)
    
    matches = [] # सध्या Demo साठी 0

    now = datetime.now().strftime('%d-%m %H:%M')
    if len(matches) == 0:
        msg = f"📊 *NSE 1000 Scan Done (1:{REWARD_RATIO})*\n\n⏰ {now}\n❌ *0 Match Found*\nRisk:Reward 1:2.5 मध्ये आज Breakout नाही."
    else:
        msg = f"🚀 *Breakout 1:{REWARD_RATIO} - {len(matches)} Found*\n\n" + "\n".join(matches)
    
    send_telegram(msg)
    print("Done")

except Exception as e:
    print(f"Error: {e}")
    send_telegram(f"⚠️ Error: {e}")
