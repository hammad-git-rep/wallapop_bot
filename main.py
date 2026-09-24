import os
import time
import threading
from flask import Flask
from curl_cffi import requests

# 1. Webserver for Render Keep-Alive
app = Flask(__name__)

@app.route('/')
def health():
    return "Wallapop Engine Active", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# 2. Config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

BARCELONA_LAT = "41.3851"
BARCELONA_LNG = "2.1734"
KEYWORDS = ["iphone 15", "macbook m1", "playstation 5"]

seen_item_ids = set()

def send_telegram_alert(title, price, url, location):
    message = (
        f"🚨 *BARCELONA DEAL DETECTED*\n\n"
        f"📌 *Item:* {title}\n"
        f"💰 *Price:* €{price}\n"
        f"📍 *Location:* {location}\n\n"
        f"🔗 [Open Listing in Wallapop]({url})"
    )
    tele_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(tele_url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

def scrape_wallapop():
    proxies = None
    if PROXY_URL and "placeholder" not in PROXY_URL:
        proxies = {"http": PROXY_URL, "https": PROXY_URL}

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "es-ES,es;q=0.9",
        "X-DeviceOS": "WEB",
        "Origin": "https://es.wallapop.com",
        "Referer": "https://es.wallapop.com/"
    }

    for keyword in KEYWORDS:
        try:
            url = f"https://api.wallapop.com/api/v3/general/search?keywords={keyword}&latitude={BARCELONA_LAT}&longitude={BARCELONA_LNG}&distance=20000&order_by=creation_date"
            
            # Use curl_cffi with impersonate="chrome120" to bypass TLS fingerprinting
            response = requests.get(
                url, 
                headers=headers, 
                proxies=proxies, 
                impersonate="chrome120", 
                timeout=12
            )
            
            print(f"Checking '{keyword}' -> Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                items = data.get("search_objects", [])
                
                for item in items[:5]:
                    item_id = item.get("id")
                    if item_id and item_id not in seen_item_ids:
                        if len(seen_item_ids) > 0:
                            title = item.get("title", "No Title")
                            price = item.get("price", "N/A")
                            web_path = item.get("web_slug", "")
                            item_url = f"https://es.wallapop.com/item/{web_path}" if web_path else "https://es.wallapop.com"
                            location = item.get("location", {}).get("city", "Barcelona")
                            
                            send_telegram_alert(title, price, item_url, location)
                            print(f"🔥 Alert sent for: {title}")
                        
                        seen_item_ids.add(item_id)
            else:
                print(f"Blocked or Error on '{keyword}': Status {response.status_code}")

        except Exception as e:
            print(f"Error scraping '{keyword}': {e}")
            
        time.sleep(4)

def engine_loop():
    print("Wallapop Engine Started - TLS Bypass Enabled...")
    send_telegram_alert("TEST ALERT - iPhone 15 Pro", "500", "[https://es.wallapop.com](https://es.wallapop.com)", "Barcelona")
    while True:
        scrape_wallapop()
        time.sleep(30)

if __name__ == "__main__":
    engine_loop()
