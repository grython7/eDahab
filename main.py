import json
import time
import os
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

WEBHOOKS = json.loads(os.environ.get("WEBHOOKS", "[]"))
EDAHAH_URL = "https://edahabapp.com/prices-dashboard"
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "180"))

GREEN = "rgba(34.12%, 96.86%, 0.00%, 1.00)"
RED   = "rgba(100.00%, 34.12%, 34.12%, 1.00)"
GRAY  = "rgba(75.00%, 75.00%, 75.00%, 1.00)"

previous_price = None


def scrape_price():
    r = session.get(
        EDAHAH_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )
    r.raise_for_status()

    text = BeautifulSoup(r.text, "lxml").get_text("\n", strip=True)
    m = re.search(
        r"عيار\s*24.*?بيع\s*([0-9][0-9,\.]*)\s*جنيه",
        text,
        flags=re.DOTALL
    )

    if not m:
        raise RuntimeError("Gold price not found")

    return float(m.group(1).replace(",", ""))


def update_webhook(webhook, current_price, previous_price):
    url = webhook["url"]
    webhook_type = webhook.get("type", "homescreen")
    name = webhook.get("name", url)

    if webhook_type == "lockscreen":
        payload = {
            "inputs": {
                "input0": f"{current_price:.0f}"
            }
        }
    else:
        if previous_price is None:
            delta = 0
            delta_percent = 0
        else:
            delta = current_price - previous_price
            delta_percent = (delta / previous_price) * 100 if previous_price else 0

        if delta > 0:
            arrow = "arrow.up"
            color = GREEN
        elif delta < 0:
            arrow = "arrow.down"
            color = RED
        else:
            arrow = "minus"
            color = GRAY

        delta_display = f"{abs(delta):.2f} ({abs(delta_percent):.2f}%)"

        payload = {
            "inputs": {
                "input0": f"{current_price:.0f}",
                "input1": arrow,
                "input2": delta_display,
                "input3": color,
                "input4": color
            }
        }

    r = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=20
    )
    r.raise_for_status()
    print(f"  [{name}] OK")


def update_all_webhooks(current_price, previous_price):
    for webhook in WEBHOOKS:
        try:
            update_webhook(webhook, current_price, previous_price)
        except Exception as e:
            name = webhook.get("name", webhook["url"])
            print(f"  [{name}] Error: {e}")


def main():
    global previous_price

    print("Gold watcher started")
    print(f"Loaded {len(WEBHOOKS)} webhook(s)")

    if not WEBHOOKS:
        print("Warning: No webhooks configured. Set WEBHOOKS in .env file.")

    while True:
        try:
            current_price = scrape_price()

            if previous_price is None or current_price != previous_price:
                print(f"Price changed: {previous_price} → {current_price}")
                update_all_webhooks(current_price, previous_price)
                previous_price = current_price
            else:
                print("No change")

        except Exception as e:
            print("Error:", e)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
