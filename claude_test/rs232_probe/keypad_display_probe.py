# Answer the keypad's polls with crafted mainboard frames and photograph
# the keypad LCD after each one (issue #10: can the PC change what the
# keypad shows?). One-off exploration; numbers below are probe values.
"""Probe what the keypad displays for crafted mainboard frames.

Usage:
    python3 keypad_display_probe.py --out DIR [--round 1] [--step-seconds S]

Safety: keypad frames are never forwarded. Each keypad poll is answered
with the probe frame, and the mainboard gets only a safe frame (speed 0,
run off, vacuum off), so the spindle cannot turn whatever the keypad
does. Every frame is logged to DIR/probe.csv and the LCD is saved as
DIR/NN_name.jpg at the end of each step, plus DIR/sheet.jpg.
"""

import argparse
import csv
import datetime
import sys
import threading
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from spincoater_midas import jp4_protocol as jp4  # noqa: E402
from spincoater_midas.bridge import Link, open_port  # noqa: E402

by_id = "/dev/serial/by-id/usb-Prolific_Technology_Inc._USB-Serial_Controller_"
keypad_default = by_id + "BHCWb144J08-if00-port0"
mainboard_default = by_id + "AUCGb144J08-if00-port0"
safe_mainboard_frame = jp4.build_keypad_frame(jp4.KeypadCommand())


def status_body(vacuum=0, speed=0, tail="0000"):
    return jp4.encode_hex_le(vacuum, 4) + jp4.encode_hex_le(speed, 4) + tail


def tail_with(position, nibble):
    tail = ["0"] * 4
    tail[position] = nibble
    return "".join(tail)


def round_one():
    steps = [
        ("baseline", status_body()),
        ("vac_643", status_body(vacuum=643)),
        ("vac_999", status_body(vacuum=999)),
        ("vac_4095", status_body(vacuum=4095)),
        ("speed_1234", status_body(speed=1234)),
        ("vac643_speed2100", status_body(vacuum=643, speed=2100)),
    ]
    for position in range(4):
        for nibble in "1248":
            tail = tail_with(position, nibble)
            steps.append((f"tail_{tail}", status_body(tail=tail)))
    steps.append(("tail_FFFF", status_body(tail="FFFF")))
    steps.append(("baseline_end", status_body()))
    return steps


def round_two():
    # Where the V mark switches on, and what happens above 999.
    readings = (1, 50, 100, 200, 299, 300, 301, 400, 500, 999, 1000, 1500)
    steps = [("baseline", status_body())]
    steps += [(f"vac_{value}", status_body(vacuum=value)) for value in readings]
    steps.append(("baseline_end", status_body()))
    return steps


class Camera(threading.Thread):
    """Keep the newest webcam frame so a snapshot is never stale."""

    def __init__(self, device):
        super().__init__(daemon=True)
        self.capture = cv2.VideoCapture(device)
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.frame = None
        self.running = True

    def run(self):
        while self.running:
            ok, frame = self.capture.read()
            if ok:
                self.frame = frame

    def save(self, path, label):
        frame = self.frame.copy()
        cv2.putText(
            frame, label, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 0, 0), 6
        )
        cv2.putText(
            frame,
            label,
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.4,
            (255, 255, 255),
            2,
        )
        cv2.imwrite(str(path), frame)
        return frame

    def stop(self):
        self.running = False
        self.join(timeout=2)
        self.capture.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keypad-port", default=keypad_default)
    parser.add_argument("--mainboard-port", default=mainboard_default)
    parser.add_argument("--out", required=True)
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--step-seconds", type=float, default=4.0)
    parser.add_argument("--camera", default="/dev/video0")
    args = parser.parse_args()
    steps = {1: round_one, 2: round_two}[args.round]()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    keypad = Link(open_port(args.keypad_port), "keypad")
    mainboard = Link(open_port(args.mainboard_port), "mainboard")
    camera = Camera(args.camera)
    camera.start()
    time.sleep(2.0)
    log_file = open(out / "probe.csv", "w", newline="")
    log = csv.writer(log_file)
    log.writerow(["wall_clock", "monotonic", "event", "detail"])

    def record(event, detail):
        log.writerow(
            [
                f"{datetime.datetime.now():%H:%M:%S.%f}",
                f"{time.monotonic():.3f}",
                event,
                detail,
            ]
        )

    thumbs = []
    keypad_bodies = set()
    try:
        for number, (name, body) in enumerate(steps):
            reply = jp4.wrap_frame(body)
            record("step", f"{name} {body}")
            print(
                f"{datetime.datetime.now():%H:%M:%S} step {number:02d} "
                f"{name:18s} to keypad {body}",
                flush=True,
            )
            polls = 0
            end = time.monotonic() + args.step_seconds
            while time.monotonic() < end:
                for frame in keypad.poll():
                    text = frame.decode("ascii", "replace")
                    record("keypad_rx", text)
                    keypad_bodies.add(text)
                    keypad.send(reply)
                    mainboard.send(safe_mainboard_frame)
                    polls += 1
                for frame in mainboard.poll():
                    record("mainboard_rx", frame.decode("ascii", "replace"))
                time.sleep(0.002)
            image = camera.save(
                out / f"{number:02d}_{name}.jpg", f"{number:02d} {name} {body}"
            )
            thumbs.append(cv2.resize(image, (640, 360)))
            record("step_end", f"{name} polls={polls}")
    finally:
        camera.stop()
        log_file.close()
    columns = 4
    blank = thumbs[0] * 0
    while len(thumbs) % columns:
        thumbs.append(blank)
    rows = [
        cv2.hconcat(thumbs[i : i + columns])
        for i in range(0, len(thumbs), columns)
    ]
    cv2.imwrite(str(out / "sheet.jpg"), cv2.vconcat(rows))
    print("keypad frames seen:", sorted(keypad_bodies))


if __name__ == "__main__":
    main()
