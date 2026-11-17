# Drive the web GUI in headless Chromium and record what the page shows
# (bench verification of the web server; kept for re-runs on the bench).
"""Operate the SPIN-1200D web page like a user and log Set/Act/Vac.

Usage:
    verify_web_gui.py --out DIR [--url URL] [--rpm R --accel A --hold H]
                      [--stop-after S]

The script waits for both link lights and for Start to be enabled
(VACUUM on at the keypad), fills the form, clicks Start, then samples
the page every 0.2 s into DIR/page.csv and saves screenshots at the
countdown, the ramp, the hold, an optional Stop click and the end.
"""

import argparse
import csv
import datetime
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_seconds = 0.2
ready_timeout = 90.0


def read_page(page) -> dict:
    lcd = page.inner_text("#lcd")
    return {
        "lcd_state": lcd.splitlines()[0].strip() if lcd else "",
        "lcd": lcd.replace("\n", " | "),
        "set_rpm": page.inner_text("#set-rpm"),
        "act_rpm": page.inner_text("#act-rpm"),
        "vacuum": page.inner_text("#vacuum"),
        "message": page.inner_text("#message"),
        "start_enabled": page.is_enabled("#start"),
        "start_action": page.get_attribute("#start", "data-action"),
    }


def as_int(text: str) -> int:
    return int(text) if text.strip().lstrip("-").isdigit() else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000/")
    parser.add_argument("--out", required=True)
    parser.add_argument("--rpm", type=int, default=2100)
    parser.add_argument("--accel", type=float, default=5.0)
    parser.add_argument("--hold", type=float, default=10.0)
    parser.add_argument("--stop-after", type=float)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1100, "height": 760})
        page.goto(args.url)
        page.wait_for_selector("#link-keypad.ok", timeout=10000)
        page.wait_for_selector("#link-mainboard.ok", timeout=10000)
        page.screenshot(path=out / "00_connected.png")
        print("page connected; waiting for Start to be enabled", flush=True)
        deadline = time.monotonic() + ready_timeout
        while not page.is_enabled("#start"):
            if time.monotonic() > deadline:
                print("gave up: " + page.inner_text("#message"))
                page.screenshot(path=out / "99_not_ready.png")
                return
            time.sleep(sample_seconds)
        page.fill("#rpm", str(args.rpm))
        page.fill("#accel", str(args.accel))
        page.fill("#hold", str(args.hold))
        page.screenshot(path=out / "01_ready_form_filled.png")

        log = open(out / "page.csv", "w", newline="")
        writer = csv.writer(log)
        fields = list(read_page(page))
        writer.writerow(["wall_clock", "seconds", *fields])
        page.click("#start")
        clicked = time.monotonic()
        print(f"clicked Start at {datetime.datetime.now():%H:%M:%S.%f}")

        shots = set()
        run_start = None
        stop_clicked = False
        finished_at = None
        target_reached = None
        max_set = max_act = 0
        while True:
            now = time.monotonic()
            values = read_page(page)
            writer.writerow(
                [
                    f"{datetime.datetime.now():%H:%M:%S.%f}",
                    f"{now - clicked:.2f}",
                ]
                + [values[name] for name in fields]
            )
            state = values["lcd_state"]
            set_rpm = as_int(values["set_rpm"])
            act_rpm = as_int(values["act_rpm"])
            if state.startswith("START") and "countdown" not in shots:
                shots.add("countdown")
                page.screenshot(path=out / "02_countdown.png")
            if state.startswith("RUN"):
                max_set = max(max_set, set_rpm)
                max_act = max(max_act, act_rpm)
                if run_start is None:
                    run_start = now
                if act_rpm >= args.rpm // 2 and "ramp" not in shots:
                    shots.add("ramp")
                    page.screenshot(path=out / "03_ramp.png")
                if target_reached is None and act_rpm >= args.rpm * 0.99:
                    target_reached = now - run_start
                if (
                    target_reached is not None
                    and now - run_start > target_reached + 3
                    and "hold" not in shots
                ):
                    shots.add("hold")
                    page.screenshot(path=out / "04_hold.png")
                if (
                    args.stop_after is not None
                    and not stop_clicked
                    and now - run_start >= args.stop_after
                ):
                    page.click("#start")  # START/STOP is one key
                    stop_clicked = True
                    print(
                        f"clicked Stop at {datetime.datetime.now():%H:%M:%S.%f}"
                        f" ({now - run_start:.2f} s into the run)"
                    )
                    page.screenshot(path=out / "05_stop_clicked.png")
            if run_start is not None and not state.startswith("RUN"):
                if finished_at is None:
                    finished_at = now
                    page.screenshot(path=out / "06_run_ended.png")
                elif now - finished_at > 3 and act_rpm == 0:
                    page.screenshot(path=out / "07_after.png")
                    break
            if run_start is None and now - clicked > 10:
                page.screenshot(path=out / "99_never_started.png")
                print("run never started: " + values["message"])
                break
            time.sleep(sample_seconds)
        log.close()
        print(f"max Set {max_set} rpm, max Act {max_act} rpm")
        if target_reached is not None:
            print(
                f"Act reached {args.rpm} rpm (99%) {target_reached:.2f} s "
                "after the page showed RUN"
            )
        print("final message: " + page.inner_text("#message"))
        browser.close()


if __name__ == "__main__":
    main()
