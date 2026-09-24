import os
import time
import requests
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def health():
    return "Wallapop Engine Online", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

def send_telegram_alert(item_title, price, url, location):
    message = f"🚨 *NEW DEAL DETECTED*\n\n📌 *Item:* {item_title}\n💰 *Price:* €{price}\n📍 *Location:* {location}\n\n🔗 [Open Listing]({url})"
    tele_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(tele_url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send alert: {e}")

def engine_loop():
    print("Wallapop Engine Started...")
    while True:
        time.sleep(30)

if __name__ == "__main__":
    engine_loop()
