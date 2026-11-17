"""Control the spin coater from a web page over a REST API.

One background thread owns both JP4 cables through a `Bridge`. It
forwards frames so the keypad keeps working, and on a web request it
counts down, runs one step from the PC, and goes back to forwarding.
The same safety gates as ``bridge run`` apply: the keypad must show
vacuum on, the vacuum must hold a substrate, and the spindle must be
still. A key press, a silent link, a vacuum drop or the web Stop
button ends a run.

Run it with::

    python3 -m spincoater_midas.server --keypad-port K --mainboard-port M

then open ``http://127.0.0.1:8000/`` in a browser on the same PC.
"""

import argparse
import csv
import datetime
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from spincoater_midas import bridge as bridge_module
from spincoater_midas.bridge import (
    Bridge,
    PortBusyError,
    RunResult,
    open_port,
)
from spincoater_midas.profile import StepProfile

# Highest speed run on this machine so far (2100 rpm, 2026-11-17).
# Raise it with --max-rpm once higher speeds have been tried by hand.
default_max_rpm = 2100
# The keypad LCD shows ACL as 00.0 s and the step time as 000.0 s, so
# these are the longest times a keypad recipe can hold.
max_acceleration_seconds = 99.9
max_hold_seconds = 999.9
page_path = Path(__file__).with_name("web") / "index.html"


class RunRequest(BaseModel):
    """Body of ``POST /api/run``."""

    rpm: int = Field(gt=0, description="Speed to reach and hold")
    accel: float = Field(
        gt=0, le=max_acceleration_seconds, description="Ramp time, s"
    )
    hold: float = Field(
        gt=0, le=max_hold_seconds, description="Time at speed, s"
    )


@dataclass
class Settings:
    """Limits fixed when the server starts.

    Attributes:
        max_rpm: Highest speed a web request may ask for.
        min_vacuum: Stop a run if the vacuum reading falls below this.
        start_vacuum: Reading needed to start a run.
    """

    max_rpm: int = default_max_rpm
    min_vacuum: int = bridge_module.default_min_vacuum
    start_vacuum: int = bridge_module.default_min_vacuum


class LockedWriter:
    """A ``csv.writer`` that the bridge thread and web requests share.

    Args:
        writer: The writer to guard.
    """

    def __init__(self, writer) -> None:
        self.writer = writer
        self.lock = threading.Lock()

    def writerow(self, row: list) -> None:
        """Write one row while holding the lock."""
        with self.lock:
            self.writer.writerow(row)


class Controller:
    """Run the bridge loop and accept run and stop requests.

    ``step`` does one unit of work and is what the background thread
    calls in a loop; tests call it directly with a simulated clock.

    Args:
        bridge: Bridge on the two JP4 cables.
        settings: Speed and vacuum limits.
    """

    def __init__(self, bridge: Bridge, settings: Settings) -> None:
        self.bridge = bridge
        self.settings = settings
        self.lock = threading.Lock()
        self.state = "forwarding"
        self.profile = None
        self.countdown_end = None
        self.run_start = None
        self.stop_requested = False
        self.last_result = None
        self.closing = False
        self.thread = None

    def request_run(self, profile: StepProfile) -> None:
        """Queue a run; it starts after the countdown.

        Raises:
            ValueError: If a run is already under way, the speed is
                over the limit, or the machine is not ready.
        """
        if profile.target_rpm > self.settings.max_rpm:
            raise ValueError(
                f"{profile.target_rpm} rpm is above the "
                f"{self.settings.max_rpm} rpm limit"
            )
        with self.lock:
            if self.state != "forwarding":
                raise ValueError(f"busy: {self.state}")
            problem = self.bridge.ready_problem(self.settings.start_vacuum)
            if problem:
                raise ValueError(problem)
            self.profile = profile
            self.stop_requested = False
            self.countdown_end = (
                self.bridge.clock() + bridge_module.countdown_seconds
            )
            self.state = "countdown"
        self.bridge.record("web_run", repr(profile))

    def request_stop(self) -> None:
        """Cancel the countdown or stop the run at once."""
        self.stop_requested = True
        self.bridge.record("web_stop", self.state)

    def step(self) -> None:
        """Forward frames, or advance the countdown, or run the step."""
        if self.state == "countdown":
            self.bridge.forward_once()
            problem = self.bridge.ready_problem(self.settings.start_vacuum)
            if self.stop_requested or problem:
                reason = (
                    "stopped from the PC" if self.stop_requested else problem
                )
                self.finish(RunResult(False, f"cancelled: {reason}", 0))
            elif self.bridge.clock() >= self.countdown_end:
                self.state = "running"
                self.run_start = self.bridge.clock()
                result = self.bridge.run_step(
                    self.profile,
                    self.settings.min_vacuum,
                    cancel=lambda: self.stop_requested,
                )
                self.finish(result)
            return
        self.bridge.forward_once()

    def finish(self, result: RunResult) -> None:
        """Record how a run ended and go back to forwarding."""
        with self.lock:
            self.last_result = result
            self.state = "forwarding"
            self.run_start = None
            self.countdown_end = None

    def status(self) -> dict:
        """Return a snapshot for the web page.

        ``set_rpm`` is the speed being commanded: the PC's command
        during a web run, otherwise the keypad's. ``act_rpm`` is the
        speed the mainboard measures.
        """
        bridge = self.bridge
        now = bridge.clock()
        command = bridge.last_command
        status = bridge.last_status
        sent = bridge.last_sent_command
        if sent is not None:
            set_rpm = sent.speed_rpm
        else:
            set_rpm = command.speed_rpm if command else None
        profile = self.profile
        return {
            "state": self.state,
            "countdown_seconds": (
                max(0.0, self.countdown_end - now)
                if self.countdown_end is not None
                else None
            ),
            "elapsed_seconds": (
                now - self.run_start if self.run_start is not None else None
            ),
            "profile": (
                {
                    "rpm": profile.target_rpm,
                    "accel": profile.acceleration_seconds,
                    "hold": profile.hold_seconds,
                }
                if profile
                else None
            ),
            "set_rpm": set_rpm,
            "act_rpm": status.speed_rpm if status else None,
            "vacuum_reading": status.vacuum_reading if status else None,
            "keypad": (
                {
                    "vacuum": command.vacuum,
                    "run": command.run,
                    "speed_rpm": command.speed_rpm,
                }
                if command
                else None
            ),
            "links": {
                "keypad": not bridge.is_quiet(bridge.last_command_time),
                "mainboard": not bridge.is_quiet(bridge.last_status_time),
            },
            "ready_problem": bridge.ready_problem(self.settings.start_vacuum),
            "last_result": (
                asdict(self.last_result) if self.last_result else None
            ),
            "bad_frames": bridge.bad_frames,
            "limits": asdict(self.settings),
        }

    def start(self) -> None:
        """Start the background thread."""
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self) -> None:
        """Call `step` until `close` is called."""
        while not self.closing:
            self.step()
            self.bridge.sleep(bridge_module.poll_seconds)

    def close(self) -> None:
        """Stop any run and end the background thread."""
        self.request_stop()
        self.closing = True
        if self.thread is not None:
            self.thread.join(timeout=5)


def create_app(controller: Controller) -> FastAPI:
    """Build the web app around a controller.

    Args:
        controller: The controller the endpoints act on.

    Returns:
        The FastAPI application.
    """
    app = FastAPI(title="SPIN-1200D web control")

    @app.get("/", include_in_schema=False)
    def page() -> FileResponse:
        return FileResponse(page_path)

    @app.get("/api/status")
    def get_status() -> dict:
        """Live state, Set/Act speed, vacuum and link health."""
        return controller.status()

    @app.post("/api/run", status_code=202)
    def post_run(request: RunRequest) -> dict:
        """Start one step after a 3 s countdown."""
        profile = StepProfile(request.rpm, request.accel, request.hold)
        try:
            controller.request_run(profile)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from None
        return controller.status()

    @app.post("/api/stop")
    def post_stop() -> dict:
        """Cancel the countdown or stop the run."""
        controller.request_stop()
        return controller.status()

    return app


def main() -> None:
    """Command-line entry point; see ``--help``."""
    import uvicorn

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keypad-port", required=True)
    parser.add_argument("--mainboard-port", required=True)
    parser.add_argument("--log", help="CSV file for every frame and event")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="address to listen on (default: this PC only; 0.0.0.0 opens "
        "it to the network, which has not been tested)",
    )
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--max-rpm", type=int, default=default_max_rpm)
    parser.add_argument(
        "--min-vacuum", type=int, default=bridge_module.default_min_vacuum
    )
    parser.add_argument("--start-vacuum", type=int)
    args = parser.parse_args()
    start_vacuum = args.start_vacuum or args.min_vacuum
    if start_vacuum < args.min_vacuum:
        parser.error("--start-vacuum must not be below --min-vacuum")

    log_file = open(args.log, "w", newline="") if args.log else None
    log = LockedWriter(csv.writer(log_file)) if log_file else None
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
    settings = Settings(args.max_rpm, args.min_vacuum, start_vacuum)
    controller = Controller(bridge, settings)
    controller.start()
    try:
        uvicorn.run(create_app(controller), host=args.host, port=args.port)
    finally:
        controller.close()
        print(f"bad frames: {bridge.bad_frames}")
        if log_file:
            log_file.close()


if __name__ == "__main__":
    main()
