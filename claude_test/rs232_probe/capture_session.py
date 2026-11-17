# Records JP4 frames (listen-only) and the webcam on one clock so key presses can be matched to frames.
import argparse
import csv
import datetime
import pathlib
import subprocess
import threading
import time

import cv2
import serial

STX = 0x02
ETX = 0x03


def stamp(epoch):
    moment = datetime.datetime.fromtimestamp(epoch)
    return moment.strftime("%H:%M:%S.%f")[:-3]


def checksum_ok(frame):
    if len(frame) < 3:
        return False
    expected = f"{sum(frame[:-2]) % 256:02X}".encode()
    return expected == frame[-2:].upper()


class Camera(threading.Thread):
    """Record the webcam with a wall-clock overlay and keep the last frame."""

    def __init__(self, device, video_path, width, height, fps, stop):
        super().__init__(daemon=True)
        self.device = device
        self.video_path = video_path
        self.width = width
        self.height = height
        self.fps = fps
        self.stop = stop
        self.lock = threading.Lock()
        self.latest = None
        self.frame_count = 0
        self.error = None
        self.ready = threading.Event()
        self.first_epoch = None
        self.last_epoch = None

    def run(self):
        # Auto exposure may lower the frame rate in dim light, which
        # makes the recording play back too fast; pin the rate instead.
        subprocess.run(
            [
                "v4l2-ctl",
                "-d",
                self.device,
                "-c",
                "exposure_dynamic_framerate=0",
            ],
            check=False,
            capture_output=True,
        )
        capture = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_FPS, self.fps)
        if not capture.isOpened():
            self.error = f"cannot open {self.device}"
            return
        size = (
            int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        writer = cv2.VideoWriter(
            str(self.video_path),
            cv2.VideoWriter_fourcc(*"mp4v"),
            self.fps,
            size,
        )
        font = cv2.FONT_HERSHEY_SIMPLEX
        while not self.stop.is_set():
            ok, image = capture.read()
            if not ok:
                continue
            now = time.time()
            if self.first_epoch is None:
                self.first_epoch = now
            self.last_epoch = now
            label = stamp(now)
            cv2.putText(image, label, (20, 50), font, 1.4, (0, 0, 0), 8)
            cv2.putText(image, label, (20, 50), font, 1.4, (255, 255, 255), 3)
            writer.write(image)
            self.frame_count += 1
            with self.lock:
                self.latest = image
            self.ready.set()
        writer.release()
        capture.release()

    def fix_playback_speed(self):
        """Retime the file to the measured frame rate, if it differs."""
        if self.frame_count < 2 or self.first_epoch is None:
            return None
        measured = (self.frame_count - 1) / (self.last_epoch - self.first_epoch)
        if abs(measured - self.fps) / self.fps < 0.02:
            return measured
        retimed = self.video_path.with_name("video_retimed.mp4")
        result = subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-y",
                "-itsscale",
                f"{self.fps / measured:.6f}",
                "-i",
                str(self.video_path),
                "-c",
                "copy",
                str(retimed),
            ],
            check=False,
            capture_output=True,
        )
        if result.returncode == 0:
            retimed.replace(self.video_path)
        return measured

    def snapshot(self, path):
        with self.lock:
            image = None if self.latest is None else self.latest.copy()
        if image is not None:
            cv2.imwrite(str(path), image)


def open_link(port, baud):
    link = serial.Serial()
    link.port = port
    link.baudrate = baud
    link.timeout = 0.05
    link.dtr = False
    link.rts = False
    link.open()
    link.reset_input_buffer()
    return link


def split_frames(buffer):
    """Pop complete STX..ETX frames from the buffer, keep the remainder."""
    frames = []
    while True:
        start = buffer.find(bytes([STX]))
        if start < 0:
            buffer.clear()
            return frames
        end = buffer.find(bytes([ETX]), start + 1)
        if end < 0:
            del buffer[:start]
            return frames
        frames.append(bytes(buffer[start + 1 : end]))
        del buffer[: end + 1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=19200)
    parser.add_argument("--camera", default="/dev/video0")
    parser.add_argument("--seconds", type=float, default=300.0)
    parser.add_argument("--label", default="session")
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).parent / "sessions",
    )
    args = parser.parse_args()

    started = time.time()
    name = datetime.datetime.fromtimestamp(started).strftime("%Y%m%d_%H%M%S")
    folder = args.root / f"{name}_{args.label}"
    (folder / "changes").mkdir(parents=True)
    stop_file = folder / "STOP"

    stop = threading.Event()
    camera = Camera(args.camera, folder / "video.mp4", 1280, 720, 15, stop)
    camera.start()
    # Wait for the first image so the first frame change gets a snapshot.
    camera.ready.wait(timeout=10)
    link = open_link(args.port, args.baud)

    total = 0
    bad = 0
    distinct = {}
    previous = None
    buffer = bytearray()
    print(f"recording to {folder} for {args.seconds:.0f} s", flush=True)
    print(f"stop early: touch {stop_file}", flush=True)
    with (
        open(folder / "frames.csv", "w", newline="") as frames_file,
        open(folder / "changes.log", "w") as changes_file,
    ):
        frames_csv = csv.writer(frames_file)
        frames_csv.writerow(["epoch", "time", "frame", "checksum_ok"])
        while time.time() - started < args.seconds and not stop_file.exists():
            buffer += link.read(256)
            for frame in split_frames(buffer):
                now = time.time()
                good = checksum_ok(frame)
                total += 1
                bad += not good
                distinct[frame] = distinct.get(frame, 0) + 1
                text = frame.decode("ascii", "backslashreplace")
                frames_csv.writerow([f"{now:.3f}", stamp(now), text, good])
                if frame != previous:
                    line = f"{stamp(now)}  {text}  ok={good}"
                    changes_file.write(line + "\n")
                    changes_file.flush()
                    print(line, flush=True)
                    picture = folder / "changes" / f"{stamp(now)}.jpg"
                    camera.snapshot(picture)
                    previous = frame
    link.close()
    stop.set()
    camera.join(timeout=5)
    measured_fps = camera.fix_playback_speed()

    summary = [
        f"started {stamp(started)}, {time.time() - started:.1f} s",
        f"frames {total}, bad checksum {bad}, distinct {len(distinct)}",
        f"video frames {camera.frame_count}, measured fps {measured_fps}, "
        f"camera error {camera.error}",
    ]
    for frame, count in sorted(distinct.items(), key=lambda item: -item[1]):
        summary.append(
            f"{count:6d}  {frame.decode('ascii', 'backslashreplace')}"
        )
    (folder / "summary.txt").write_text("\n".join(summary) + "\n")
    print("\n".join(summary), flush=True)


if __name__ == "__main__":
    main()
