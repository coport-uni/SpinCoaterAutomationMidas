# Press the web page's VACUUM key and log what the page shows; then wait
# for the operator's keypad VACUUM press (bench check of issue #10).
"""Check the shared vacuum state through the web page.

Usage:
    verify_web_vacuum.py --out DIR [--url URL] [--wait-keypad SECONDS]

Sequence: page VACUUM on, off, on (5 s each), then wait for the operator
to press VACUUM on the machine's keypad, which should switch it off.
Every 0.2 s the page's LCD line 1, Vac tile and the API's vacuum_on are
written to DIR/vacuum.csv; a screenshot is saved after each change.
"""

import argparse
import csv
import datetime
import json
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_seconds = 0.2
hold_seconds = 5.0


def api_status(url: str) -> dict:
    with urllib.request.urlopen(url + "api/status") as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/")
    parser.add_argument("--out", required=True)
    parser.add_argument("--wait-keypad", type=float, default=60.0)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log = open(out / "vacuum.csv", "w", newline="")
    writer = csv.writer(log)
    writer.writerow(
        ["wall_clock", "phase", "lcd_line1", "page_vac", "api_vacuum_on"]
    )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 760})
        page.goto(args.url)
        page.wait_for_selector("#link-mainboard.ok", timeout=10000)

        def sample(phase: str, seconds: float) -> dict:
            end = time.monotonic() + seconds
            status = {}
            while time.monotonic() < end:
                status = api_status(args.url)
                writer.writerow(
                    [
                        f"{datetime.datetime.now():%H:%M:%S.%f}",
                        phase,
                        page.inner_text("#lcd").splitlines()[0],
                        page.inner_text("#vacuum"),
                        status["vacuum_on"],
                    ]
                )
                time.sleep(sample_seconds)
            return status

        start = sample("start", 2.0)
        print(
            f"start: vacuum_on={start['vacuum_on']} "
            f"reading={start['vacuum_reading']}"
        )
        for number, want in enumerate((True, False, True), start=1):
            if api_status(args.url)["vacuum_on"] != want:
                page.click("#key-vacuum")
            status = sample(f"page_{'on' if want else 'off'}", hold_seconds)
            page.screenshot(path=out / f"{number:02d}_page_vacuum_{want}.png")
            print(
                f"{datetime.datetime.now():%H:%M:%S} page VACUUM -> "
                f"vacuum_on={status['vacuum_on']} "
                f"reading={status['vacuum_reading']}",
                flush=True,
            )

        print("waiting for the keypad VACUUM press", flush=True)
        end = time.monotonic() + args.wait_keypad
        while time.monotonic() < end:
            if not api_status(args.url)["vacuum_on"]:
                status = sample("after_keypad", hold_seconds)
                page.screenshot(path=out / "04_after_keypad_press.png")
                print(
                    f"{datetime.datetime.now():%H:%M:%S} keypad press -> "
                    f"vacuum_on={status['vacuum_on']} "
                    f"reading={status['vacuum_reading']}"
                )
                break
            sample("waiting_keypad", sample_seconds)
        else:
            print("no keypad press seen")
        browser.close()
    log.close()


if __name__ == "__main__":
    main()
