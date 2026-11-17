"""Tests for the web server, on the simulated keypad and mainboard."""

from fastapi.testclient import TestClient
from test_bridge import (
    empty_chuck_vacuum,
    fault_time,
    frame_period,
    make_bench,
    reaction_seconds,
    scenario,
    sent_commands,
    wafer_vacuum,
)

from spincoater_midas import bridge as bridge_module
from spincoater_midas.server import Controller, Settings, create_app

run_body = {
    "rpm": scenario.target_rpm,
    "accel": scenario.acceleration_seconds,
    "hold": scenario.hold_seconds,
}
settle_seconds = 1.0


def make_server(**bench_options):
    """Build a controller and a test client on a simulated bench."""
    bench, clock, keypad_port, mainboard_port = make_bench(**bench_options)
    controller = Controller(bench, Settings())
    client = TestClient(create_app(controller))
    return controller, client, clock, mainboard_port


def drive(controller, clock, seconds, action_at=None):
    """Run the controller loop for a while on simulated time.

    Args:
        action_at: Optional ``(time, function)``; the function is called
            once when the simulated clock reaches that time, even in the
            middle of a run.
    """
    pending = [action_at] if action_at else []
    real_sleep = controller.bridge.sleep

    def sleep(step):
        real_sleep(step)
        if pending and clock.now >= pending[0][0]:
            pending.pop()[1]()

    controller.bridge.sleep = sleep
    end = clock.now + seconds
    while clock.now < end:
        controller.step()
        sleep(bridge_module.poll_seconds)
    controller.bridge.sleep = real_sleep


def test_page_is_served():
    _, client, _, _ = make_server()
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="act-rpm"' in response.text


def test_status_while_forwarding():
    controller, client, clock, _ = make_server()
    drive(controller, clock, settle_seconds)
    status = client.get("/api/status").json()
    assert status["state"] == "forwarding"
    assert status["act_rpm"] == 0
    assert status["vacuum_reading"] == wafer_vacuum
    assert status["links"] == {"keypad": True, "mainboard": True}
    assert status["ready_problem"] == ""


def test_run_refused_on_empty_chuck():
    controller, client, clock, _ = make_server(
        vacuum_at=lambda t: empty_chuck_vacuum
    )
    drive(controller, clock, settle_seconds)
    response = client.post("/api/run", json=run_body)
    assert response.status_code == 409
    assert "below" in response.json()["detail"]


def test_run_refused_above_speed_limit():
    controller, client, clock, _ = make_server()
    drive(controller, clock, settle_seconds)
    body = dict(run_body, rpm=controller.settings.max_rpm + 1)
    response = client.post("/api/run", json=body)
    assert response.status_code == 409
    assert "limit" in response.json()["detail"]


def test_run_refused_for_out_of_range_times():
    _, client, _, _ = make_server()
    too_long = dict(run_body, hold=1000.0)
    assert client.post("/api/run", json=too_long).status_code == 422


def test_web_run_completes_after_countdown():
    controller, client, clock, mainboard_port = make_server()
    drive(controller, clock, settle_seconds)
    requested = clock.now
    assert client.post("/api/run", json=run_body).status_code == 202
    assert client.post("/api/run", json=run_body).status_code == 409

    statuses = []
    run_seconds = bridge_module.countdown_seconds + scenario.total_seconds
    middle = requested + bridge_module.countdown_seconds + fault_time
    drive(
        controller,
        clock,
        run_seconds + settle_seconds,
        action_at=(middle, lambda: statuses.append(controller.status())),
    )
    assert controller.status()["last_result"]["completed"]
    running = [(t, c) for t, c in sent_commands(mainboard_port) if c.run]
    first_run_time = running[0][0]
    assert first_run_time - requested >= bridge_module.countdown_seconds
    assert max(c.speed_rpm for _, c in running) == scenario.target_rpm
    middle_status = statuses[0]
    assert middle_status["state"] == "running"
    assert middle_status["set_rpm"] > 0
    assert middle_status["act_rpm"] > 0


def test_stop_during_countdown_sends_no_run():
    controller, client, clock, mainboard_port = make_server()
    drive(controller, clock, settle_seconds)
    client.post("/api/run", json=run_body)
    drive(controller, clock, settle_seconds)
    client.post("/api/stop")
    drive(controller, clock, bridge_module.countdown_seconds)
    status = controller.status()
    assert status["state"] == "forwarding"
    assert "cancelled" in status["last_result"]["reason"]
    assert not any(c.run for _, c in sent_commands(mainboard_port))


def test_stop_during_run_stops_the_spindle():
    controller, client, clock, mainboard_port = make_server()
    drive(controller, clock, settle_seconds)
    client.post("/api/run", json=run_body)
    stop_time = clock.now + bridge_module.countdown_seconds + fault_time
    drive(
        controller,
        clock,
        bridge_module.countdown_seconds + scenario.total_seconds,
        action_at=(stop_time, controller.request_stop),
    )
    status = controller.status()
    assert not status["last_result"]["completed"]
    assert "PC" in status["last_result"]["reason"]
    commands = sent_commands(mainboard_port)
    last_running = max(t for t, c in commands if c.run)
    assert last_running - stop_time < reaction_seconds
    after = [c for t, c in commands if t > last_running + frame_period]
    assert after and all(c.speed_rpm == 0 and not c.run for c in after)
