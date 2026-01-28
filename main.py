import time
import os
import re
import requests
from bs4 import BeautifulSoup

PUSHCUT_WEBHOOK = os.environ["PUSHCUT_WEBHOOK"]
EDAHAH_URL = "https://edahabapp.com/"

POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "180"))

GREEN = "rgba(34.12%, 96.86%, 0.00%, 1.00)"
RED   = "rgba(100.00%, 34.12%, 34.12%, 1.00)"
GRAY  = "rgba(75.00%, 75.00%, 75.00%, 1.00)"

previous_price = None


def scrape_price():
    r = requests.get(
        EDAHAH_URL,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"}
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


def update_pushcut_widget(current_price, previous_price):
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
        PUSHCUT_WEBHOOK,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=20
    )
    r.raise_for_status()


def main():
    global previous_price

    print("Gold watcher started")

    while True:
        try:
            current_price = scrape_price()

            if previous_price is None or current_price != previous_price:
                update_pushcut_widget(current_price, previous_price)
                print(f"Updated: {previous_price} → {current_price}")
                previous_price = current_price
            else:
                print("No change")

        except Exception as e:
            print("Error:", e)

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()