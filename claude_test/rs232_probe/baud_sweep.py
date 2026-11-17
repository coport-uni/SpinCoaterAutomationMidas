# Listen-only baud sweep on the KW-525 to find the JP4 link speed; never writes to the port.
import argparse
import datetime
import pathlib
import time

import serial

BAUDS = [2400, 4800, 9600, 14400, 19200, 38400, 57600, 115200]


def listen(port, baud, seconds):
    link = serial.Serial()
    link.port = port
    link.baudrate = baud
    link.timeout = 0.1
    # Keep the modem lines low; only RXD, TXD and GND are wired.
    link.dtr = False
    link.rts = False
    link.open()
    link.reset_input_buffer()
    data = bytearray()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        data += link.read(256)
    link.close()
    return bytes(data)


def describe(data):
    if not data:
        return "no bytes"
    printable = sum(32 <= b < 127 or b in (10, 13) for b in data)
    distinct = len(set(data))
    return (
        f"{len(data):5d} bytes, {distinct:3d} distinct, "
        f"{100 * printable / len(data):5.1f}% printable"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/ttyUSB0")
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--bauds", type=int, nargs="*", default=BAUDS)
    parser.add_argument("--log", type=pathlib.Path)
    args = parser.parse_args()

    lines = [
        f"# {datetime.datetime.now().isoformat(timespec='seconds')} "
        f"port={args.port} seconds={args.seconds}"
    ]
    for baud in args.bauds:
        data = listen(args.port, baud, args.seconds)
        lines.append(f"{baud:6d}: {describe(data)}")
        lines.append(f"        hex: {data[:64].hex(' ')}")
        lines.append(f"        txt: {data[:64]!r}")
    report = "\n".join(lines)
    print(report)
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        args.log.write_text(report + "\n")


if __name__ == "__main__":
    main()
