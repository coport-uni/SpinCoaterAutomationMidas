"""Put the PC between keypad and mainboard on JP4 (wiring B).

Two RS-232 cables replace the Blue and White wires. Cable 1 faces the
keypad: it receives keypad frames and sends mainboard frames to the
keypad. Cable 2 faces the mainboard: it sends keypad frames to the
mainboard and receives mainboard frames.

Modes:
    listen   Read both cables, write nothing.
    forward  Pass frames through so the front panel works as before.
    run      Drive one recipe step from the PC while mainboard frames
             keep reaching the keypad LCD.

The run stops the spindle (speed 0, run off, vacuum kept on so the
substrate stays held) as soon as anything looks wrong: a key changes
the keypad frame, either side goes quiet, or the vacuum reading drops.
"""

import argparse
import csv
import datetime
import time
from dataclasses import dataclass

from spincoater_midas import jp4_protocol as jp4
from spincoater_midas.profile import StepProfile

# The keypad sends about 19.2 frames per second (bench, 2026-11-17).
send_period_seconds = 0.052
poll_seconds = 0.002
# A side counts as silent after this long without a valid frame
# (about ten missed frames).
silence_limit_seconds = 0.5
# After a step or an abort, keep sending the stop frame this long so
# the mainboard is sure to see it before forwarding resumes.
stop_hold_seconds = 0.5
# Vacuum with a wafer read 643; an empty chuck read 163. A run needs a
# reading between the two to be sure a substrate is held.
default_min_vacuum = 400
# How long `run` waits for the operator to switch the vacuum on.
ready_timeout_seconds = 60.0
countdown_seconds = 3


def stop_frame(baseline: jp4.KeypadCommand) -> bytes:
    """Build a frame for speed 0 and run off, with the vacuum kept on.

    Args:
        baseline: Keypad command whose constant fields are copied.

    Returns:
        The complete frame, ready to send to the mainboard.
    """
    return jp4.build_keypad_frame(
        jp4.KeypadCommand(
            speed_rpm=0,
            vacuum=True,
            run=False,
            prefix=baseline.prefix,
            tail=baseline.tail,
        )
    )


class Link:
    """One serial cable with its frame splitter."""

    def __init__(self, port, name: str) -> None:
        self.port = port
        self.name = name
        self.splitter = jp4.FrameSplitter()

    def poll(self) -> list[bytes]:
        """Return every complete frame received since the last poll."""
        waiting = self.port.in_waiting
        if not waiting:
            return []
        return self.splitter.feed(self.port.read(waiting))

    def send(self, frame: bytes) -> None:
        """Write one complete frame (with STX and ETX)."""
        self.port.write(frame)


@dataclass
class RunResult:
    """Outcome of one `Bridge.run_step` call.

    Attributes:
        completed: True if the whole step ran without an abort.
        reason: Why the run ended.
        peak_measured_rpm: Highest speed the mainboard reported.
    """

    completed: bool
    reason: str
    peak_measured_rpm: int


class Bridge:
    """Frame-level bridge between the keypad and mainboard cables.

    Args:
        keypad_port: Serial port wired to the keypad side.
        mainboard_port: Serial port wired to the mainboard side.
        clock: Monotonic clock in seconds; injectable for tests.
        sleep: Sleep function; injectable for tests.
        log: Optional ``csv.writer`` for every frame and event.
    """

    def __init__(
        self,
        keypad_port,
        mainboard_port,
        clock=time.monotonic,
        sleep=time.sleep,
        log=None,
    ) -> None:
        self.keypad = Link(keypad_port, "keypad")
        self.mainboard = Link(mainboard_port, "mainboard")
        self.clock = clock
        self.sleep = sleep
        self.log = log
        self.last_command = None
        self.last_command_time = None
        self.last_status = None
        self.last_status_time = None
        self.bad_frames = 0
        # The command the PC is sending during a run; None otherwise.
        self.last_sent_command = None
        # Set after a PC run; see `forward_once`. It also starts set, so a
        # bridge started while the keypad is mid-recipe (for example right
        # after another bridge process aborted a run) does not adopt it.
        self.stop_latched = True

    def record(self, event: str, detail: str = "") -> None:
        """Write one line to the session log, if there is one."""
        if self.log is not None:
            self.log.writerow([f"{self.clock():.3f}", event, detail])

    def read_keypad(self) -> list[bytes]:
        """Poll the keypad cable and remember the latest valid command."""
        frames = []
        for frame in self.keypad.poll():
            try:
                self.last_command = jp4.parse_keypad_frame(frame)
            except jp4.FrameError:
                self.bad_frames += 1
                self.record("keypad_bad", frame.decode("ascii", "replace"))
                continue
            self.last_command_time = self.clock()
            self.record("keypad_rx", frame.decode("ascii"))
            frames.append(frame)
        return frames

    def read_mainboard(self) -> list[bytes]:
        """Poll the mainboard cable and remember the latest status."""
        frames = []
        for frame in self.mainboard.poll():
            try:
                self.last_status = jp4.parse_mainboard_frame(frame)
            except jp4.FrameError:
                self.bad_frames += 1
                self.record("mainboard_bad", frame.decode("ascii", "replace"))
                continue
            self.last_status_time = self.clock()
            self.record("mainboard_rx", frame.decode("ascii"))
            frames.append(frame)
        return frames

    def is_quiet(self, last_time) -> bool:
        """True if a side has not sent a valid frame recently."""
        return (
            last_time is None
            or self.clock() - last_time > silence_limit_seconds
        )

    def listen_once(self) -> None:
        """Read both cables without writing anything."""
        self.read_keypad()
        self.read_mainboard()

    def keypad_idle(self) -> bool:
        """True if the keypad is not running a recipe of its own."""
        command = self.last_command
        return not command.run and not command.speed_rpm

    def forward_once(self) -> None:
        """Pass every valid frame through to the other side.

        After a PC run, a stop frame replaces each keypad frame until the
        keypad itself is idle. START and STOP are one key, so pressing it
        during a PC run starts the keypad's own recipe; without the latch
        that recipe would take over the spindle when forwarding resumed
        (bench, 2026-11-17).
        """
        for frame in self.read_keypad():
            if self.stop_latched and not self.keypad_idle():
                frame = stop_frame(self.last_command)
                self.record("to_mainboard", frame[1:-1].decode("ascii"))
                self.mainboard.send(frame)
                continue
            if self.stop_latched:
                self.stop_latched = False
                self.record("stop_released", "keypad is idle")
            self.mainboard.send(jp4.wrap_frame(frame[:-2].decode("ascii")))
        for frame in self.read_mainboard():
            self.keypad.send(jp4.wrap_frame(frame[:-2].decode("ascii")))

    def spin(self, seconds: float, step) -> None:
        """Call ``step`` repeatedly for a number of seconds."""
        end = self.clock() + seconds
        while self.clock() < end:
            step()
            self.sleep(poll_seconds)

    def ready_problem(self, min_vacuum: int) -> str:
        """Explain why a run may not start, or return an empty string."""
        if self.is_quiet(self.last_command_time):
            return "no frames from the keypad"
        if self.is_quiet(self.last_status_time):
            return "no frames from the mainboard"
        command = self.last_command
        if command.run or command.speed_rpm:
            return "keypad is running its own recipe"
        if not command.vacuum:
            return "vacuum is off (press VACUUM on the keypad)"
        if self.last_status.speed_rpm:
            return "spindle is still turning"
        if self.last_status.vacuum_reading < min_vacuum:
            return (
                f"vacuum reading {self.last_status.vacuum_reading} is "
                f"below {min_vacuum} (is a substrate on the chuck?)"
            )
        return ""

    def send_stop(self, baseline: jp4.KeypadCommand) -> None:
        """Command speed 0 and run off, keeping vacuum, for a moment."""
        stop = stop_frame(baseline)
        self.last_sent_command = jp4.parse_keypad_frame(stop)
        end = self.clock() + stop_hold_seconds
        next_send = self.clock()
        while self.clock() < end:
            if self.clock() >= next_send:
                self.mainboard.send(stop)
                self.record("to_mainboard", stop[1:-1].decode("ascii"))
                next_send += send_period_seconds
            for frame in self.read_mainboard():
                self.keypad.send(jp4.wrap_frame(frame[:-2].decode("ascii")))
            self.read_keypad()
            self.sleep(poll_seconds)

    def run_step(
        self, profile: StepProfile, min_vacuum: int, cancel=None
    ) -> RunResult:
        """Drive one step from the PC, then hand back to the keypad.

        Call only when `ready_problem` returns an empty string. Keypad
        frames are watched but not forwarded during the run; mainboard
        frames keep going to the keypad.

        Args:
            profile: Speed, acceleration time and hold time.
            min_vacuum: Abort if the vacuum reading falls below this.
            cancel: Optional function polled during the run; the run
                stops as soon as it returns True (the web Stop button).

        Returns:
            Whether the step completed, and why the run ended.
        """
        baseline = self.last_command
        start = self.clock()
        next_send = start
        peak = 0
        reason = ""
        self.record("run_start", repr(profile))
        try:
            while True:
                now = self.clock()
                elapsed = now - start
                if elapsed >= profile.total_seconds:
                    break
                if now >= next_send:
                    command = jp4.KeypadCommand(
                        speed_rpm=profile.command_at(elapsed),
                        vacuum=True,
                        run=True,
                        prefix=baseline.prefix,
                        tail=baseline.tail,
                    )
                    frame = jp4.build_keypad_frame(command)
                    self.mainboard.send(frame)
                    self.last_sent_command = command
                    self.record("to_mainboard", frame[1:-1].decode("ascii"))
                    next_send += send_period_seconds
                for frame in self.read_mainboard():
                    self.keypad.send(jp4.wrap_frame(frame[:-2].decode("ascii")))
                    peak = max(peak, self.last_status.speed_rpm)
                if cancel is not None and cancel():
                    reason = "stopped from the PC"
                    break
                for _ in self.read_keypad():
                    if self.last_command != baseline:
                        reason = "keypad frame changed (a key was pressed)"
                if not reason and self.is_quiet(self.last_command_time):
                    reason = "keypad went quiet"
                if not reason and self.is_quiet(self.last_status_time):
                    reason = "mainboard went quiet"
                if not reason and self.last_status.vacuum_reading < min_vacuum:
                    reason = (
                        f"vacuum dropped to {self.last_status.vacuum_reading}"
                    )
                if reason:
                    break
                self.sleep(poll_seconds)
        except KeyboardInterrupt:
            reason = "interrupted by the operator"
        finally:
            self.send_stop(baseline)
            self.stop_latched = True
            self.last_sent_command = None
        completed = not reason
        reason = reason or "step completed"
        self.record("run_end", reason)
        return RunResult(completed, reason, peak)


class PortBusyError(RuntimeError):
    """A JP4 cable is already open in another program."""


def open_port(path: str):
    """Open one JP4 cable: 19200 8N1, non-blocking, modem lines low.

    The port is locked, so the bridge and the web server (or two copies
    of either) cannot both send frames to the mainboard.

    Raises:
        PortBusyError: If another program holds the port.
    """
    import serial

    port = serial.Serial()
    port.port = path
    port.baudrate = jp4.baud_rate
    port.timeout = 0
    port.dtr = False
    port.rts = False
    port.exclusive = True
    try:
        port.open()
    except serial.SerialException as error:
        if "lock" not in str(error):
            raise
        raise PortBusyError(
            f"{path} is in use; is the bridge or the server already running?"
        ) from error
    port.reset_input_buffer()
    return port


def identify(paths: list[str], seconds: float = 2.0) -> dict[str, str]:
    """Report which cable hears the keypad and which the mainboard.

    Only reads; nothing is written. The cable that receives ``C``
    frames is on the keypad side.

    Args:
        paths: Serial device paths to check.
        seconds: Listening time per port.

    Returns:
        Map from path to ``"keypad"``, ``"mainboard"``, ``"silent"``, or
        ``"busy"`` if another program holds the port.
    """
    roles = {}
    for path in paths:
        try:
            port = open_port(path)
        except PortBusyError:
            roles[path] = "busy"
            continue
        splitter = jp4.FrameSplitter()
        frames = []
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            frames += splitter.feed(port.read(port.in_waiting or 1))
        port.close()
        keypad_frames = sum(1 for f in frames if f.startswith(b"C"))
        if not frames:
            roles[path] = "silent"
        elif keypad_frames > len(frames) // 2:
            roles[path] = "keypad"
        else:
            roles[path] = "mainboard"
    return roles


def main() -> None:
    """Command-line entry point; see ``--help``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keypad-port")
    parser.add_argument("--mainboard-port")
    parser.add_argument("--log", help="CSV file for every frame and event")
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("identify", help="find which port faces which board")
    for name, text in (
        ("listen", "log both directions, write nothing"),
        ("forward", "pass frames both ways so the keypad works"),
    ):
        mode = sub.add_parser(name, help=text)
        mode.add_argument("--seconds", type=float, default=60.0)
    run = sub.add_parser("run", help="drive one step from the PC")
    run.add_argument("--rpm", type=int, required=True)
    run.add_argument("--accel", type=float, required=True)
    run.add_argument("--hold", type=float, required=True)
    run.add_argument(
        "--min-vacuum",
        type=int,
        default=default_min_vacuum,
        help="stop the run if the vacuum reading falls below this",
    )
    run.add_argument(
        "--start-vacuum",
        type=int,
        help="reading needed to start (default: --min-vacuum); set it "
        "above --min-vacuum so reading noise cannot stop a run at once",
    )
    run.add_argument(
        "--yes",
        action="store_true",
        help="confirm that the operator is at the machine",
    )
    args = parser.parse_args()

    if args.mode == "identify":
        import glob

        paths = sorted(glob.glob("/dev/serial/by-id/*"))
        for path, role in identify(paths).items():
            print(f"{role:9s} {path}")
        return
    if not (args.keypad_port and args.mainboard_port):
        parser.error("--keypad-port and --mainboard-port are required")
    if args.mode == "run" and not args.yes:
        parser.error("run needs --yes: the operator must be at the machine")
    if args.mode == "run":
        if args.start_vacuum is None:
            args.start_vacuum = args.min_vacuum
        if args.start_vacuum < args.min_vacuum:
            parser.error("--start-vacuum must not be below --min-vacuum")

    log_file = open(args.log, "w", newline="") if args.log else None
    log = csv.writer(log_file) if log_file else None
    if log:
        log.writerow(["monotonic", "event", "detail"])
        log.writerow(
            [f"{time.monotonic():.3f}", "wall_clock", datetime.datetime.now()]
        )
    try:
        ports = open_port(args.keypad_port), open_port(args.mainboard_port)
    except PortBusyError as error:
        parser.exit(1, f"error: {error}\n")
    bridge = Bridge(*ports, log=log)
    try:
        if args.mode == "listen":
            bridge.spin(args.seconds, bridge.listen_once)
        elif args.mode == "forward":
            bridge.spin(args.seconds, bridge.forward_once)
        else:
            profile = StepProfile(args.rpm, args.accel, args.hold)
            deadline = time.monotonic() + ready_timeout_seconds
            problem = "waiting"
            while problem and time.monotonic() < deadline:
                bridge.spin(0.5, bridge.forward_once)
                problem = bridge.ready_problem(args.start_vacuum)
                if problem:
                    print(f"not ready: {problem}", flush=True)
            if problem:
                print("gave up waiting; nothing was started")
                return
            for count in range(countdown_seconds, 0, -1):
                print(f"starting in {count} s (Ctrl+C to cancel)", flush=True)
                bridge.spin(1.0, bridge.forward_once)
                problem = bridge.ready_problem(args.start_vacuum)
                if problem:
                    print(f"cancelled: {problem}")
                    return
            result = bridge.run_step(profile, args.min_vacuum)
            print(
                f"{result.reason}; peak measured {result.peak_measured_rpm} rpm"
            )
            bridge.spin(2.0, bridge.forward_once)
    except KeyboardInterrupt:
        print("stopped by the operator")
    finally:
        last = bridge.last_status
        print(f"bad frames: {bridge.bad_frames}; last mainboard status: {last}")
        if log_file:
            log_file.close()


if __name__ == "__main__":
    main()
