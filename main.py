import os
import time
import threading
from flask import Flask
from curl_cffi import requests

# 1. Flask App Setup (Render Keep-Alive Endpoint)
app = Flask(__name__)

@app.route('/')
def health():
    return "Wallapop Engine Active", 200

# 2. Environment Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PROXY_URL = os.environ.get("PROXY_URL")

BARCELONA_LAT = "41.3851"
BARCELONA_LNG = "2.1734"

# 3. Targeted Product Matrix with Custom Price Boundaries
TARGET_CONFIG = [
    {"keyword": "iphone x", "min": 40, "max": 80},
    {"keyword": "iphone xr", "min": 40, "max": 90},
    {"keyword": "iphone 11", "min": 60, "max": 130},
    {"keyword": "iphone 11 pro", "min": 80, "max": 140},
    {"keyword": "iphone 12", "min": 90, "max": 150},
    {"keyword": "iphone 12 pro", "min": 100, "max": 170},
    {"keyword": "iphone 13", "min": 100, "max": 180},
    {"keyword": "iphone 13 pro", "min": 140, "max": 280},
    {"keyword": "iphone 14", "min": 140, "max": 220},
    {"keyword": "iphone 14 pro", "min": 250, "max": 400},
    {"keyword": "iphone 15", "min": 240, "max": 375},
    {"keyword": "iphone 15 pro", "min": 300, "max": 450}
]

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
        print(f"Failed to send Telegram alert: {e}", flush=True)

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

    for target in TARGET_CONFIG:
        kw = target["keyword"]
        min_p = target["min"]
        max_p = target["max"]

        try:
            url = (
                f"https://api.wallapop.com/api/v3/general/search?"
                f"keywords={kw}&latitude={BARCELONA_LAT}&longitude={BARCELONA_LNG}"
                f"&distance=20000&min_sale_price={min_p}&max_sale_price={max_p}"
                f"&order_by=creation_date"
            )
            
            response = requests.get(
                url, 
                headers=headers, 
                proxies=proxies, 
                impersonate="chrome120", 
                timeout=12
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("search_objects", [])
                
                for item in items[:3]:
                    item_id = item.get("id")
                    if item_id and item_id not in seen_item_ids:
                        if len(seen_item_ids) > 0:
                            title = item.get("title", "No Title")
                            price = item.get("price", "N/A")
                            web_path = item.get("web_slug", "")
                            item_url = f"https://es.wallapop.com/item/{web_path}" if web_path else "https://es.wallapop.com"
                            location = item.get("location", {}).get("city", "Barcelona")
                            
                            send_telegram_alert(title, price, item_url, location)
                            print(f"🔥 Alert sent for: {title} (€{price})", flush=True)
                        
                        seen_item_ids.add(item_id)
            else:
                print(f"Blocked or Error on '{kw}': Status {response.status_code}", flush=True)

        except Exception as e:
            print(f"Error scraping '{kw}': {e}", flush=True)
            
        # 2.5s delay per model to protect proxy IP reputation across 12 cycles
        time.sleep(2.5)

def engine_loop():
    print("Wallapop Engine Started - Scaled iPhone Sweep Active...", flush=True)
    while True:
        scrape_wallapop()
        # Rest 15 seconds after completing a full pass through all 12 models
        time.sleep(15)

if __name__ == "__main__":
    # Launch scraper background thread before starting web server
    scraper_thread = threading.Thread(target=engine_loop, daemon=True)
    scraper_thread.start()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
