"""Tests for the wiring-B bridge, with simulated keypad and mainboard.

The simulated mainboard follows the last speed it was commanded, and
both sides send a frame every 52 ms like the real boards.
"""

import pytest

from spincoater_midas import bridge as bridge_module
from spincoater_midas import jp4_protocol as jp4
from spincoater_midas.bridge import Bridge
from spincoater_midas.profile import StepProfile

frame_period = 0.052
# Test scenario requested for wiring B: 2100 rpm in 5 s, hold 10 s.
scenario = StepProfile(
    target_rpm=2100, acceleration_seconds=5.0, hold_seconds=10.0
)
wafer_vacuum = 643
empty_chuck_vacuum = 163
min_vacuum = bridge_module.default_min_vacuum
# When a fault is injected, partway through the run.
fault_time = 3.0
# Allow one send period plus the silence limit to detect a fault.
reaction_seconds = frame_period + bridge_module.silence_limit_seconds

keypad_idle_vacuum = jp4.KeypadCommand(vacuum=True)
keypad_idle = jp4.KeypadCommand()


class FakeClock:
    """Shared simulated time; `sleep` advances it."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakePort:
    """A serial port whose far end sends one frame per period.

    Args:
        clock: Shared simulated clock.
        source: Called with the send time; returns a frame body, or
            None to stay silent.
    """

    def __init__(self, clock: FakeClock, source) -> None:
        self.clock = clock
        self.source = source
        self.next_time = 0.0
        self.pending = bytearray()
        self.written = []

    @property
    def in_waiting(self) -> int:
        while self.clock.now >= self.next_time:
            body = self.source(self.next_time)
            if body is not None:
                self.pending += jp4.wrap_frame(body)
            self.next_time += frame_period
        return len(self.pending)

    def read(self, size: int) -> bytes:
        data = bytes(self.pending[:size])
        del self.pending[:size]
        return data

    def write(self, data: bytes) -> None:
        self.written.append((self.clock.now, data))


def keypad_body(command: jp4.KeypadCommand) -> str:
    return jp4.build_keypad_frame(command)[1:-3].decode("ascii")


def mainboard_body(vacuum: int, speed: int) -> str:
    return jp4.encode_hex_le(vacuum, 4) + jp4.encode_hex_le(speed, 4) + "0000"


def last_commanded_speed(port: FakePort) -> int:
    for _, data in reversed(port.written):
        return jp4.parse_keypad_frame(data).speed_rpm
    return 0


def make_bench(keypad_source=None, vacuum_at=None, mainboard_silent_at=None):
    """Build a bridge on simulated ports.

    Args:
        keypad_source: Keypad frame body per time; idle with vacuum on
            by default.
        vacuum_at: Vacuum reading per time; a wafer by default.
        mainboard_silent_at: Time after which the mainboard stops.
    """
    clock = FakeClock()
    keypad_source = keypad_source or (lambda t: keypad_body(keypad_idle_vacuum))
    vacuum_at = vacuum_at or (lambda t: wafer_vacuum)
    keypad_port = FakePort(clock, keypad_source)
    mainboard_port = FakePort(clock, None)

    def mainboard_source(t):
        if mainboard_silent_at is not None and t >= mainboard_silent_at:
            return None
        return mainboard_body(
            vacuum_at(t), last_commanded_speed(mainboard_port)
        )

    mainboard_port.source = mainboard_source
    bench = Bridge(keypad_port, mainboard_port, clock=clock, sleep=clock.sleep)
    return bench, clock, keypad_port, mainboard_port


def sent_commands(port: FakePort, since: float = 0.0):
    return [
        (t, jp4.parse_keypad_frame(data))
        for t, data in port.written
        if t >= since
    ]


def start_run(bench, clock):
    """Let frames arrive, check readiness, then run the scenario."""
    bench.spin(1.0, bench.forward_once)
    assert bench.ready_problem(min_vacuum) == ""
    start = clock.now
    return start, bench.run_step(scenario, min_vacuum)


def test_profile_reaches_target_one_update_before_acl_ends():
    update = 0.1
    assert scenario.command_at(0.0) == scenario.target_rpm // 50
    assert scenario.command_at(scenario.acceleration_seconds - 2 * update) < (
        scenario.target_rpm
    )
    assert scenario.command_at(scenario.acceleration_seconds - update) == (
        scenario.target_rpm
    )
    assert scenario.command_at(scenario.total_seconds - update) == (
        scenario.target_rpm
    )
    assert scenario.command_at(scenario.total_seconds) == 0
    assert scenario.command_at(-update) == 0


def test_profile_never_steps_down_during_ramp():
    times = [k * 0.01 for k in range(int(scenario.total_seconds * 100))]
    speeds = [scenario.command_at(t) for t in times]
    assert all(after >= before for before, after in zip(speeds, speeds[1:]))


def test_listen_writes_nothing():
    bench, _, keypad_port, mainboard_port = make_bench()
    bench.spin(1.0, bench.listen_once)
    assert keypad_port.written == [] and mainboard_port.written == []
    assert bench.last_command == keypad_idle_vacuum
    assert bench.last_status.vacuum_reading == wafer_vacuum


def test_forward_passes_frames_both_ways_unchanged():
    bench, _, keypad_port, mainboard_port = make_bench()
    bench.spin(1.0, bench.forward_once)
    to_mainboard = {data for _, data in mainboard_port.written}
    to_keypad = {data for _, data in keypad_port.written}
    assert to_mainboard == {jp4.build_keypad_frame(keypad_idle_vacuum)}
    assert to_keypad == {jp4.wrap_frame(mainboard_body(wafer_vacuum, 0))}


def test_run_refused_without_vacuum():
    bench, _, _, _ = make_bench(
        keypad_source=lambda t: keypad_body(keypad_idle)
    )
    bench.spin(1.0, bench.forward_once)
    assert "vacuum is off" in bench.ready_problem(min_vacuum)


def test_run_refused_on_empty_chuck():
    bench, _, _, _ = make_bench(vacuum_at=lambda t: empty_chuck_vacuum)
    bench.spin(1.0, bench.forward_once)
    assert "below" in bench.ready_problem(min_vacuum)


def test_run_completes_scenario_and_stops():
    bench, clock, keypad_port, mainboard_port = make_bench()
    start, result = start_run(bench, clock)

    assert result.completed
    assert result.peak_measured_rpm == scenario.target_rpm
    commands = sent_commands(mainboard_port, since=start)
    running = [(t, c) for t, c in commands if c.run]
    assert all(c.vacuum for _, c in commands)
    assert max(c.speed_rpm for _, c in running) == scenario.target_rpm
    assert running[-1][0] - start == pytest.approx(
        scenario.total_seconds, abs=frame_period
    )
    after = [c for t, c in commands if t > running[-1][0]]
    assert after and all(c.speed_rpm == 0 and not c.run for c in after)
    # The keypad kept receiving mainboard frames during the run.
    assert any(t > start for t, _ in keypad_port.written)


def assert_aborted_near_fault(result, mainboard_port, start, keyword):
    assert not result.completed
    assert keyword in result.reason
    commands = sent_commands(mainboard_port, since=start)
    last_running = max(t for t, c in commands if c.run)
    assert last_running - start < fault_time + reaction_seconds
    stops = [c for t, c in commands if t > last_running]
    assert stops and all(c.speed_rpm == 0 and c.vacuum for c in stops)


def test_key_press_aborts_run():
    def keypad_source(t):
        command = (
            keypad_idle_vacuum
            if t < run_start[0] + fault_time
            else (keypad_idle)
        )
        return keypad_body(command)

    run_start = [float("inf")]
    bench, clock, _, mainboard_port = make_bench(keypad_source=keypad_source)
    bench.spin(1.0, bench.forward_once)
    run_start[0] = clock.now
    result = bench.run_step(scenario, min_vacuum)
    assert_aborted_near_fault(result, mainboard_port, run_start[0], "keypad")


def test_mainboard_silence_aborts_run():
    first_run_time = 1.0
    bench, clock, _, mainboard_port = make_bench(
        mainboard_silent_at=first_run_time + fault_time
    )
    start, result = start_run(bench, clock)
    assert start == pytest.approx(first_run_time, abs=frame_period)
    assert_aborted_near_fault(result, mainboard_port, start, "mainboard")


def test_vacuum_loss_aborts_run():
    first_run_time = 1.0
    bench, clock, _, mainboard_port = make_bench(
        vacuum_at=lambda t: (
            wafer_vacuum
            if t < first_run_time + fault_time
            else empty_chuck_vacuum
        )
    )
    start, result = start_run(bench, clock)
    assert_aborted_near_fault(result, mainboard_port, start, "vacuum")


def test_keypad_recipe_started_mid_run_does_not_take_over():
    """START/STOP during a PC run starts the keypad's own recipe.

    The run must stop, and forwarding must not hand the spindle to that
    recipe: the mainboard gets stop frames until the keypad is idle.
    """
    keypad_recipe_seconds = 5.0
    keypad_recipe = jp4.KeypadCommand(speed_rpm=1234, vacuum=True, run=True)

    def keypad_source(t):
        fault = run_start[0] + fault_time
        if fault <= t < fault + keypad_recipe_seconds:
            return keypad_body(keypad_recipe)
        return keypad_body(keypad_idle_vacuum)

    run_start = [float("inf")]
    bench, clock, _, mainboard_port = make_bench(keypad_source=keypad_source)
    bench.spin(1.0, bench.forward_once)
    run_start[0] = clock.now
    result = bench.run_step(scenario, min_vacuum)
    assert_aborted_near_fault(result, mainboard_port, run_start[0], "keypad")

    recipe_end = run_start[0] + fault_time + keypad_recipe_seconds
    abort_time = clock.now
    bench.spin(keypad_recipe_seconds + 1.0, bench.forward_once)
    after_abort = sent_commands(mainboard_port, since=abort_time)
    during_recipe = [c for t, c in after_abort if t < recipe_end]
    after_recipe = [c for t, c in after_abort if t > recipe_end + frame_period]
    assert during_recipe
    assert all(c.speed_rpm == 0 and not c.run for c in during_recipe)
    assert after_recipe and all(c == keypad_idle_vacuum for c in after_recipe)
    assert not bench.stop_latched


def test_new_bridge_does_not_adopt_a_running_keypad_recipe():
    keypad_recipe = jp4.KeypadCommand(speed_rpm=1234, vacuum=True, run=True)
    recipe_end = 2.0
    bench, _, _, mainboard_port = make_bench(
        keypad_source=lambda t: keypad_body(
            keypad_recipe if t < recipe_end else keypad_idle_vacuum
        )
    )
    bench.spin(recipe_end + 1.0, bench.forward_once)
    commands = sent_commands(mainboard_port)
    during = [c for t, c in commands if t < recipe_end]
    after = [c for t, c in commands if t > recipe_end + frame_period]
    assert during and all(c.speed_rpm == 0 and not c.run for c in during)
    assert after and all(c == keypad_idle_vacuum for c in after)


def test_cancel_stops_the_run():
    cancel_time = 1.0 + fault_time
    bench, clock, _, mainboard_port = make_bench()
    start, result = None, None
    bench.spin(1.0, bench.forward_once)
    start = clock.now
    result = bench.run_step(
        scenario, min_vacuum, cancel=lambda: clock.now >= cancel_time
    )
    assert_aborted_near_fault(result, mainboard_port, start, "PC")
    assert bench.last_sent_command is None


def test_last_sent_command_shows_the_stop():
    """The web page's Set must read 0 while the stop frame is sent."""
    bench, clock, _, mainboard_port = make_bench()
    bench.spin(1.0, bench.forward_once)
    shown_with_stop = []
    real_send = bench.mainboard.send

    def send(frame):
        if not jp4.parse_keypad_frame(frame).run:
            shown_with_stop.append(bench.last_sent_command)
        real_send(frame)

    bench.mainboard.send = send
    bench.run_step(scenario, min_vacuum)
    assert shown_with_stop
    assert all(c.speed_rpm == 0 and not c.run for c in shown_with_stop)
