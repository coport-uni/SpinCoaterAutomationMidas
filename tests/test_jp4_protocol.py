"""Tests for the JP4 frame format, using frames recorded on the bench.

Fixtures in ``tests/data`` are windows of the 2026-11-17 recordings
under ``claude_test/rs232_probe/sessions``:

- ``keypad_run_1234rpm.csv``: Blue, one-step recipe (1234 rpm, 5 s,
  ACL 5 s), vacuum on, START, end, vacuum off.
- ``mainboard_run_1234rpm.csv``: White, same set speed, wafer on chuck.
- ``mainboard_vacuum_empty_chuck.csv``: White, vacuum on with an empty
  chuck while the LCD read ``Vac -163``.
"""

import csv
import pathlib
import statistics

import pytest

from spincoater_midas import jp4_protocol as protocol

data_dir = pathlib.Path(__file__).parent / "data"

# Recipe and LCD values from the bench session, not fitted to the code.
set_speed_rpm = 1234
acceleration_seconds = 5.0
step_seconds = 5.0
lcd_empty_chuck_vacuum = 163

# Timing tolerance: the keypad updates the command about every 100 ms
# and the host clock stamps frames as they arrive.
timing_tolerance_seconds = 0.2
# One ramp increment is 1234 rpm / 50 updates, so 24 or 25 rpm.
ramp_increments_rpm = {0, 24, 25}
# The measured speed wanders a few rpm around the set point.
speed_tolerance_rpm = 5
# The LCD shows a smoothed value; allow one count either way.
lcd_vacuum_tolerance = 1
# Skip the pump-down before averaging the vacuum reading.
vacuum_settle_seconds = 3.0

# Values read off the LCD at the moment these frames were recorded.
first_ramp_speed_rpm = 24
wafer_vacuum_reading = 643
plateau_speed_rpm = 1232

keypad_idle = "C21000000000" + "56"
keypad_vacuum = "C21000002000" + "58"
keypad_running = "C2102D403000" + "73"
keypad_first_ramp_step = "C21081003000" + "62"
mainboard_idle = "000000000000" + "40"
mainboard_running = "38200D400000" + "65"


def load_frames(name):
    """Return (seconds of day, frame text) pairs from a fixture CSV."""
    rows = []
    with open(data_dir / name, newline="") as fixture:
        for row in csv.DictReader(fixture):
            hours, minutes, seconds = row["time"].split(":")
            stamp = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            rows.append((stamp, row["frame"]))
    return rows


def test_checksum_matches_recorded_idle_frames():
    assert protocol.compute_checksum(keypad_idle[:-2]) == keypad_idle[-2:]
    assert protocol.compute_checksum(mainboard_idle[:-2]) == mainboard_idle[-2:]


def test_hex_field_is_low_nibble_first():
    assert protocol.decode_hex_le("2D40") == set_speed_rpm
    assert protocol.encode_hex_le(set_speed_rpm, 4) == "2D40"


def test_hex_field_rejects_values_that_do_not_fit():
    with pytest.raises(ValueError):
        protocol.encode_hex_le(16**4, 4)
    with pytest.raises(ValueError):
        protocol.encode_hex_le(-1, 4)


def test_parse_keypad_states():
    assert protocol.parse_keypad_frame(keypad_idle) == protocol.KeypadCommand()
    assert protocol.parse_keypad_frame(keypad_vacuum) == protocol.KeypadCommand(
        vacuum=True
    )
    assert protocol.parse_keypad_frame(keypad_running) == (
        protocol.KeypadCommand(speed_rpm=set_speed_rpm, vacuum=True, run=True)
    )


def test_build_keypad_frame_reproduces_recorded_bytes():
    command = protocol.KeypadCommand(
        speed_rpm=set_speed_rpm, vacuum=True, run=True
    )
    expected = (
        bytes([protocol.stx]) + keypad_running.encode() + bytes([protocol.etx])
    )
    assert protocol.build_keypad_frame(command) == expected


def test_parse_accepts_frames_with_stx_and_etx():
    framed = protocol.wrap_frame(keypad_first_ramp_step[:-2])
    assert protocol.parse_keypad_frame(framed).speed_rpm == (
        first_ramp_speed_rpm
    )


def test_bad_checksum_is_rejected():
    corrupted = keypad_idle[:-2] + "57"
    with pytest.raises(protocol.FrameError):
        protocol.parse_keypad_frame(corrupted)


def test_keypad_parser_rejects_mainboard_frame():
    # The reverse check is impossible: a keypad body such as
    # "C21000000000" is also twelve valid hex characters, so the
    # direction has to come from which wire the frame was read on.
    with pytest.raises(protocol.FrameError):
        protocol.parse_keypad_frame(mainboard_idle)


def test_mainboard_parser_rejects_wrong_length():
    short_body = mainboard_idle[:-3]
    with pytest.raises(protocol.FrameError):
        protocol.parse_mainboard_frame(
            short_body + protocol.compute_checksum(short_body)
        )


def test_parse_mainboard_running_frame():
    status = protocol.parse_mainboard_frame(mainboard_running)
    assert status.vacuum_reading == wafer_vacuum_reading
    assert status.speed_rpm == plateau_speed_rpm
    assert status.tail == "0000"


def test_every_recorded_keypad_frame_round_trips():
    for _, frame in load_frames("keypad_run_1234rpm.csv"):
        command = protocol.parse_keypad_frame(frame)
        assert protocol.build_keypad_frame(command) == protocol.wrap_frame(
            frame[:-2]
        )


def test_keypad_ramp_matches_recipe():
    commands = [
        (stamp, protocol.parse_keypad_frame(frame))
        for stamp, frame in load_frames("keypad_run_1234rpm.csv")
    ]
    assert all(c.run == (c.speed_rpm > 0) for _, c in commands)

    speeds = [c.speed_rpm for _, c in commands if c.run]
    steps = {after - before for before, after in zip(speeds, speeds[1:])}
    assert steps <= ramp_increments_rpm
    assert max(speeds) == set_speed_rpm

    start = next(stamp for stamp, c in commands if c.run)
    at_speed = next(
        stamp for stamp, c in commands if c.speed_rpm == set_speed_rpm
    )
    end = next(stamp for stamp, c in commands if stamp > at_speed and not c.run)
    assert at_speed - start == pytest.approx(
        acceleration_seconds, abs=timing_tolerance_seconds
    )
    assert end - start == pytest.approx(
        acceleration_seconds + step_seconds, abs=timing_tolerance_seconds
    )


def test_mainboard_speed_holds_near_set_point():
    speeds = [
        protocol.parse_mainboard_frame(frame).speed_rpm
        for _, frame in load_frames("mainboard_run_1234rpm.csv")
    ]
    near_set_point = [
        i
        for i, speed in enumerate(speeds)
        if abs(speed - set_speed_rpm) <= speed_tolerance_rpm
    ]
    # From reaching the set point until the stop begins, no frame may
    # leave the tolerance band. The ramp and the stop are excluded.
    plateau = speeds[near_set_point[0] : near_set_point[-1] + 1]
    assert all(
        abs(speed - set_speed_rpm) <= speed_tolerance_rpm for speed in plateau
    )


def test_mainboard_vacuum_matches_lcd():
    readings = [
        (stamp, protocol.parse_mainboard_frame(frame).vacuum_reading)
        for stamp, frame in load_frames("mainboard_vacuum_empty_chuck.csv")
    ]
    switched_on = next(stamp for stamp, value in readings if value > 0)
    steady = [
        value
        for stamp, value in readings
        if stamp > switched_on + vacuum_settle_seconds and value > 0
    ]
    assert statistics.mean(steady) == pytest.approx(
        lcd_empty_chuck_vacuum, abs=lcd_vacuum_tolerance
    )


def test_splitter_handles_arbitrary_chunks():
    stream = (
        b"\x7f\x00"
        + protocol.wrap_frame(keypad_idle[:-2])
        + protocol.wrap_frame(keypad_running[:-2])
    )
    splitter = protocol.FrameSplitter()
    frames = []
    for index in range(len(stream)):
        frames += splitter.feed(stream[index : index + 1])
    assert frames == [keypad_idle.encode(), keypad_running.encode()]
    assert splitter.buffer == bytearray()
