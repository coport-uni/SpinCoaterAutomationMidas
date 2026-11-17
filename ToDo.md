# ToDo

## Adopt CommonClaude harness and hooks

### Background
User request (2026-11-17): add https://github.com/coport-uni/CommonClaude
as a submodule under `external/`, then apply its Claude Code harness and
hooks to this repository.
Issue: https://github.com/coport-uni/SpinCoaterAutomationMidas/issues/1

### Tasks
- [x] Add `external/CommonClaude` as a git submodule
- [x] Copy `.claude/settings.json` (env, Pre/PostToolUse hooks, Stop hook)
- [x] Copy the five hook scripts into `.claude/hooks/`
- [x] Create root `CLAUDE.md` that imports
      `@external/CommonClaude/CLAUDE.md`
- [x] Smoke-test each hook with sample JSON input
- [x] Register GitHub issue via `gh issue create` (#1)
- [ ] Commit on a working branch and open a PR (awaiting user approval)

### Notes
- The generic credential patterns in `pre-bash-secret-scan.sh` are
  case-sensitive, so an all-uppercase key name is not detected while a
  lowercase one is. Inherited from upstream CommonClaude.

## Plan: automate the Midas 1200D via the keypad-mainboard link

### Background
User request (2026-11-17): adapt the approach of
https://github.com/coport-uni/SpinCoaterAutomationLaurell to the Midas
1200D. The keypad board (Midas MS-SN-KB12D) reaches the mainboard
through a four-wire header, JP4. Chip photographs are in `docs/`.
Status: DRAFT -- awaiting user confirmation. No issue or branch yet.

### Parts identified from the photographs
- ATmega128A-AU (TQFP-64) with an external crystal: the keypad has its
  own firmware, unlike the passive I2C keypad on the Laurell.
- Sipex SP3232EEA (SSOP-16) with four charge-pump caps (C8-C11):
  RS-232 transceiver, so JP4 most likely carries a UART at RS-232
  levels (inferred, not measured).
- 24LC256 (SOIC-8): 32 KB I2C EEPROM, probably recipe storage.
- D1, D2 SMAJ30CA: bidirectional TVS diodes, likely on the JP4 lines.
- U4: unpopulated 20-pin footprint, purpose unknown.
- JP3: 6-pin header, purpose unknown (ISP is one candidate).
- Q2 + R6 next to a two-pad circle: likely a buzzer driver.

### Tasks
- [ ] Photograph the mainboard and its end of the four-wire cable
- [ ] Stage 0 (power off): trace JP4 pins by continuity to GND, VCC,
      SP3232 pins 13/14 (R1IN/T1OUT) or 7/8 (R2IN/T2OUT)
- [x] Stage 0 (powered, operator present): measure idle voltage on each
      JP4 pin to confirm RS-232 levels (about +/-5.5 V) and VCC
- [ ] Stage 1: passive sniff on the TTL side of the SP3232
      (T1IN pin 11, R1OUT pin 12) with a logic analyzer; find baud
      rate and frame format
- [ ] Stage 2: record every operation (idle, edit recipe, vacuum on/off,
      start, each step change, stop, lid open, error) and decode the
      protocol into `docs/` (direction, framing, checksum, fields)
- [ ] Decide architecture: full keypad replacement by the host vs.
      man-in-the-middle that keeps the front panel working
- [ ] Stage 3: inject commands from the host through a USB-RS232
      adapter, operator present, low RPM, empty chuck first
- [ ] Stage 4: Python host library with state-based waits and a
      safety stop path; tests under `tests/`
- [ ] Optional: read the 24LC256 recipe layout; do not touch ATmega
      fuses or lock bits

### Notes
- Never connect RS-232 lines directly to a 3.3 V or 5 V MCU pin.
- Do not bypass the lid or vacuum interlocks at any stage.

## Record the JP4 voltage measurement in docs

### Background
User request (2026-11-17): the operator measured the voltage between
every pair of the four JP4 wires and asked for the photo of the sheet
to be organized into `docs/`.

### Tasks
- [x] Copy the sheet photo to `docs/jp4_voltage_matrix.jpg`
- [x] Transcribe the readings and interpretation into
      `docs/jp4_voltage_measurement.md`
- [x] Confirm polarity of each wire against Black
- [x] Find which of White/Blue is keypad TX by continuity to SP3232

### Notes
- Inferred: Red = +5 V VCC, Black = GND, White and Blue = RS-232 data
  lines idling near -4.4 V. The matrix is consistent only with this
  assignment if Red is positive; polarity was not recorded.

## Register the Midas automation plan as a GitHub issue

### Background
User request (2026-11-17): create an issue from the work so far. This
also confirms the draft plan above.

### Tasks
- [x] Create the issue with the plan, parts list, JP4 measurement and
      reference-search result
      (https://github.com/coport-uni/SpinCoaterAutomationMidas/issues/2)

## Record JP4 data-line direction

### Background
User report (2026-11-17): Blue has continuity to SP3232 pin 14 (T1OUT).

### Tasks
- [x] Record Blue = keypad TX in `docs/jp4_voltage_measurement.md`
- [x] Comment the result on issue #2
- [ ] Confirm White to SP3232 pin 13 (R1IN)

## Draw the KW-525 DB9 wiring

### Background
User request (2026-11-17): show visually where DB9 pins 2, 3 and 5 are
on the KW-525 (Prolific PL-2303) USB-RS232 cable and how they connect
to JP4.

### Tasks
- [x] Draw both connector faces (male cable end, mating female
      adapter) and the pin-to-wire table in
      `docs/diagrams/db9_pinout.svg`
- [x] Publish a viewable wiring page
      (https://claude.ai/artifact/Q8z3aBuuaGxDQJzoThriBa)

## Check the KW-525 and webcam, plan the signal measurement

### Background
User request (2026-11-17): DB9 pins 2, 3 and 5 are wired, a Logitech
webcam watches the keypad LCD. Verify both devices and write up how the
signals will be measured. Also store the front panel photo in `docs/`.

### Tasks
- [x] Confirm the KW-525 enumerates (`/dev/ttyUSB0`, PL-2303) and the
      C920 enumerates (`/dev/video0`)
- [x] Capture one webcam frame of the LCD
      (`claude_test/rs232_probe/cam_standby.jpg`)
- [x] Listen-only baud sweep; 19200 bps gives clean frames
      (`claude_test/rs232_probe/`)
- [x] Decode the idle frame and its checksum
- [x] Save the front panel photo as `docs/front_panel_buttons.jpg`
- [x] Write `docs/jp4_protocol.md` with findings and measurement plan
- [ ] Confirm where DB9 pin 3 (TXD) is connected and that it does not
      share a line with a live transmitter
- [ ] Run measurement Phase A steps 2-5 with the operator
- [ ] Run Phase B with the tap moved to White

### Notes
- Frame: STX, 'C', 12 ASCII digits, 2 hex-ASCII checksum (byte sum of
  command and digits mod 256), ETX. 19.2 frames per second at idle.

## DB9 pin 3 location and revised next steps

### Background
User report (2026-11-17): DB9 pin 3 (TXD) is wired to JP4 White, in
parallel with the mainboard transmitter on that line.

### Tasks
- [ ] Power off and disconnect DB9 pin 3 from White until a transmit
      test is scheduled (the KW-525 drives TXD at idle even with the
      port closed, so it contends with the mainboard on White)
- [ ] Phase A steps 2-5 on Blue with a timestamped capture tool that
      also saves a webcam frame on each frame change
- [ ] Phase B on White (second KW-525 recommended for both directions
      at once)
- [ ] Parser and checksum module with tests under `tests/`, using the
      recorded logs as fixtures
- [ ] First transmit test: host to keypad on White with the mainboard
      side of White opened (no motor path)
- [ ] Keypad replacement: pin 3 to Blue, pin 2 to White, keypad off
      the link, operator present
- [ ] Check what the mainboard does when frames stop mid-run

## Phase A step 1: capture tool with webcam recording

### Background
User request (2026-11-17): PC-only control is the target, with the
LCD content eventually shown on the PC. Start Phase A and record the
webcam so key-press timing can be matched to frames.

### Tasks
- [x] Write `claude_test/rs232_probe/capture_session.py` (listen-only
      frame log, change log, webcam video with time overlay, snapshot
      on each change)
- [x] Dry run: 180 frames, 0 bad checksums, video retimed to 15 fps
- [x] Correct the frame description: 11 digits, not 12 (checksum only
      matches with 11); fixed in `docs/jp4_protocol.md` and logs
- [ ] Explain the digit-8 change (`0` to `2`) seen at 08:51:15
- [ ] Re-aim the camera so the right-hand button group is in frame
- [ ] Phase A step 2 session: rpm, time and ACL edits

### Notes
- Correction to the earlier entry "Check the KW-525 and webcam":
  the frame has 11 ASCII digits, not 12.

## Phase A step 2, first session result

### Background
Session 08:53:40 (user performed EDIT and rpm edits).

### Tasks
- [x] Find the 161.5 s frame gap and match it to EDIT mode in the video
- [x] Record that frames stayed `2100` while the LCD showed 2200 rpm
- [ ] Rerun step 2 with one edit per EDIT visit and 10 s in STANDBY
      after each, using distinctive values (1234 rpm, 012.3 s, 04.5 s)

## Phase A step 2b result

### Tasks
- [x] Rerun step 2 with one edit per EDIT visit (session 08:58:06)
- [x] Record: LCD showed every edit, frames never changed; setpoints
      are not streamed in STANDBY
- [ ] Disconnect DB9 pin 3 from White before Phase B and step 5
- [ ] Step 4: VACUUM on/off on Blue
- [ ] Phase B idle and VACUUM on White (pin 2 moved, pin 3 removed)
- [ ] Step 5: one-step run at a distinctive rpm (e.g. 1234 rpm, 5 s),
      operator present, to see whether START sends the setpoints

## Save webcam footage and stills for the README

### Background
User request (2026-11-17): keep the webcam videos and photos so they
can be used when the README is written.

### Tasks
- [x] Re-encode the two step-2 session videos to H.264 720p CRF 28
      (17 MB, 22 MB; originals 83 MB and 131 MB stay uncommitted)
- [x] Make a 12x time-lapse GIF of the setpoint-edit session (5.7 MB)
- [x] Copy five stills into `docs/media/images/`
- [x] Index everything in `docs/media/index.md`

## Phase A step 4: VACUUM on Blue

### Background
User report (2026-11-17): DB9 pin 3 is now disconnected from White.

### Tasks
- [x] DB9 pin 3 disconnected (user)
- [x] Record VACUUM on/off twice on Blue and compare frames
      (three cycles recorded; digit 8 = vacuum command)

## Phase B: listen on White (mainboard to keypad)

### Background
User report (2026-11-17): DB9 pin 2 moved to White; pin 3 stays
disconnected.

### Tasks
- [x] Baud sweep on White: 19200 bps, frame `STX 000000000000 40 ETX`
      (12 digits, no command letter, same checksum rule)
      (`claude_test/rs232_probe/sweep_02_white.log`)
- [x] Record idle and VACUUM on/off on White (session 09:15:49):
      characters 1-2 = vacuum reading, hex, low nibble first
- [ ] Step 5 run on White, then on Blue (operator present)

## Phase A/B step 5: first low-rpm run

### Background
User setup (2026-11-17): step 1 = 1234 rpm, 005.0 s, ACL 05.0 s;
wafer on the vacuum chuck. Operator presses START; host listens only.

### Tasks
- [x] Confirm step 1 on the LCD via webcam
- [ ] Operator confirms steps 2-5, lid closed, e-stop in reach
- [x] Record the run on White (session 09:27:08); steps 2-5 also ran
      by accident. Characters 5-7 = speed; steps 2-5 field/LCD mismatch
- [x] Find how to delete steps: manual excerpt on manualzz; recorded in
      `docs/front_panel_operation.md`. Recipe A now `Stp01/01` (user)
- [x] Operator observation: chuck kept spinning at a similar speed in
      steps 2-5, so the mainboard speed field is the real speed
- [x] Record the run on Blue (session 09:37:07): digits 4-7 = commanded
      speed, digit 8 bit 0 = run, keypad generates the ramp

## JP4 protocol parser with tests

### Background
User request (2026-11-17): build the parser for both JP4 directions,
with tests based on the recorded sessions. PC-only control is the
target, so one KW-525 will do (TXD to Blue, RXD from White).

### Tasks
- [x] Cut branch `feature/jp4-protocol-parser`
- [x] Add `pyproject.toml` with Ruff line length 80 and pytest config
- [x] Add `spincoater_midas/jp4_protocol.py`: checksum, little-endian
      hex fields, keypad command and mainboard status parse/build,
      stream frame splitter
- [x] Add `tests/test_jp4_protocol.py` with frames from the recorded
      sessions as fixtures
- [x] Run pytest, `ruff check`, `ruff format --check` and show output

### Notes
- 15 tests pass. Two first-run failures were wrong test expectations:
  a keypad body is also a valid mainboard body (direction must come
  from the wire), and the mainboard plateau check had included the
  stop transient (1232 -> 669 -> 3 -> 0).
- Added `.gitignore` from CommonClaude section 13.

## README for first-time users, and wiring B

### Background
User request (2026-11-17): wiring B (PC in the middle of Blue/White,
keypad kept) chosen; the user is wiring it now. Meanwhile, write the
README for someone handling this spin coater for the first time, with
heavy use of visuals. README in English per CommonClaude section 2.

### Tasks
- [x] Generate figures (frame anatomy, run speed/vacuum chart, wiring B,
      DB9 faces) and check each one visually
- [x] Write `README.md`: machine tour, LCD, keypad board, JP4 protocol,
      evidence media, hardware setups (listen, B, PC-only), software,
      safety, open questions
- [x] Check every README claim against docs, logs and code
- [ ] Test wiring B once the user finishes it (listen first, then forward)
- [x] Verify figures for text overlaps with an automated check
      (`make_figures.py` measures text boxes against text, lines and
      shapes); fixed 3 overlaps in `run_profile.png`, now 0 in all four

## Merge to main, then wiring B bridge

### Background
User request (2026-11-17): merge the work so far to `main`, then write
the code for wiring B. Test scenario for B: reach 2100 rpm in 5 s
(ACL 5.0 s) and hold 2100 rpm for 10 s.

### Tasks
- [x] Commit on `feature/jp4-protocol-parser`, push, open PR, merge
      (PR #3, merged 2026-11-17)
- [x] New branch for the bridge; write the forward/override program
- [x] GitHub issue for the bridge work (#4)
- [x] Bench test with the operator: forwarding only, then the 2100 rpm
      scenario

### Notes
- Bridge code (`spincoater_midas/bridge.py`, `profile.py`) and 10 tests
  with simulated boards; 25 tests pass. A mutation check (each abort
  disabled in turn, then the stop frame) made the suite fail every
  time.
- Not committed yet: device code must run on the machine first
  (CommonClaude section 5.1).
- Both cables enumerate: `...AUCGb144J08...` = ttyUSB0,
  `...BHCWb144J08...` = ttyUSB1. Which faces which board is decided by
  `bridge identify` once the wiring is done.

## Check wiring B

### Tasks
- [x] `bridge identify`: BHCW (ttyUSB1) hears keypad frames = keypad
      side, as the user said; AUCG (ttyUSB0) silent
- [x] Keypad frames clean (0 bad); LCD on STANDBY, so Red/Black pass
- [x] Found: keypad polls; with no reply it retries every ~2.1 s, and
      the mainboard stays silent (recorded in `docs/jp4_protocol.md`)
- [x] Verify the transmit paths with a short `forward` run (needs the
      operator's go-ahead; STANDBY frames only)

## Bench step 1: keypad run through the bridge

### Background
User request (2026-11-17): "1번 해보자". Forward for 150 s while the
operator turns VACUUM on and starts a low-rpm one-step recipe from the
keypad. The host only forwards; all motion is started by the operator.
Issue #4.

### Tasks
- [x] Start `bridge forward --seconds 150` with webcam recording
      (`claude_test/rs232_probe/sessions/20261117_103447_bridge_forward_keypad_run/`)
- [x] Analyse the log: frame counts, bad frames, poll rate, commanded
      vs measured speed, vacuum (0 bad; 1234 rpm reached at 4.91 s,
      hold mean 1231.6 rpm; stop 0.41 s; poll 13.5/s while running)
- [x] Check the LCD in the video; record results in docs and issue #4
      (`lcd_sequence.jpg`: STANDBY Vac -634, RUN Act 1234 rpm, END)

## Bench step 2: 2100 rpm scenario driven by the PC

### Background
User request (2026-11-17): "완료되는대로 2단계도 해보자". Run
`bridge run --rpm 2100 --accel 5 --hold 10 --yes` with a wafer on the
chuck, the operator at the machine with the e-stop. The bridge waits
up to 60 s for the operator to turn VACUUM on (vacuum >= 400), counts
down 3 s, runs, stops, then forwards 2 s. Issue #4.

### Tasks
- [x] Start the run with log and webcam recording
- [x] Analyse: ramp time, hold speed, stop, aborts, LCD
- [x] Record results in docs, claude_test README and issue #4
- [x] User request "진공펌프를 꺼줄래?": with the bridge stopped the
      keypad cannot reach the mainboard, so the host sent vacuum-off
      frames for 3 s; vacuum 643 to 0, speed 0 (`vacuum_off.csv`)

## Commit the bridge, PR, and a README terminal walkthrough

### Background
User request (2026-11-17): "그렇게해줘 Readme에도 이 레포를 터미널에서
어떻게 다루는지 example 세션을 만들어줘." Commit the bench-verified
bridge, push, open a PR with the bench output; add an example terminal
session to the README built from real command output. Issue #4.

### Tasks
- [x] README: example terminal session (setup, tests, identify,
      listen, forward, run) with real output
- [x] ruff and pytest on the final tree
- [x] Commit on `feature/jp4-bridge`, push, open PR (Testing = bench
      output); merge only when the user asks (PR #5)
- [ ] Before merging: try the abort paths on the machine (key press,
      link silence, vacuum loss); they are marked NOT VERIFIED in PR #5

## Abort tests on the machine, merge PR #5, then web control

### Background
User request (2026-11-17): "테스트하고 머지해줘. 원래 계획대로 터미널
상에서 restapi를 사용해서 웹서버에서 띠우고 스핀코터 제어할 수 있게
해줘. 실제 웹사이트의 GUI를 조작해서 RPM이나 ACT 값이 변화하는지
확인해서 검증해줘"

### Part 1: abort paths on the machine (PR #5)
All at low speed (500 rpm, ACL 3 s, hold 20 s), wafer on, lid closed,
operator at the e-stop, log + webcam for each.
- [x] T1 key press: operator presses STOP on the keypad mid-run. Learn
      whether STOP changes the keypad frame; if not, repeat with VACUUM
  - First try (10:58): START/STOP is one key, so the press started the
    keypad's recipe; the run stopped, but forwarding then let that
    recipe spin up to 1241 rpm. Fix: after a PC run, send stop frames
    instead of keypad frames until the keypad is idle; new test
    `test_keypad_recipe_started_mid_run_does_not_take_over` (fails
    without the fix). Repeat T1 on the machine.
- [x] T2 keypad link lost: operator pulls the keypad-side DB9 mid-run;
      expect "keypad went quiet" and a stop within about 0.5 s
- [x] T3 vacuum drop: `--min-vacuum 642`, just above the readings seen
      during a run (640-645), so a real reading trips the check
- [x] T4a mainboard link lost: operator pulls the mainboard-side DB9
      mid-run at 300 rpm; the PC cannot send the stop, so this shows
      what the mainboard does on its own; re-plug, `forward` stops it
- [x] T4b PC down: kill -9 the bridge mid-run at 300 rpm; after 5 s
      `forward` resumes, and its first reply shows whether the spindle
      kept turning (user chose both T4a and T4b)
- [x] Put the results in PR #5's Testing section; merge; delete branch

### Part 2: web control over a REST API (new issue, branch
`feature/web-control`)
- [ ] Server process owns both cables: forwards by default so the keypad
      works, takes over for a PC run, then forwards again
- [ ] REST API: `GET /api/status` (state, Set/Act rpm, vacuum, keypad
      flags), `POST /api/run` (rpm, accel, hold), `POST /api/stop`
- [ ] Web page: LCD-style panel (Set, Act, Vac, state) updated live,
      run form, Start and Stop buttons
- [ ] Same safety gates as `bridge run`: vacuum on with a substrate,
      spindle still; Stop button aborts at once
- [ ] Tests on the simulated ports; ruff
- [ ] Verify on the machine through the browser GUI (automated
      browser): set rpm, Start, watch Act rise and hold, Stop; webcam
      and screenshots as evidence
- [ ] README section; commit, push, PR with the evidence
- [x] Bridge starts latched too, so a new `forward` process does not
      adopt a keypad recipe that was already running; test
      `test_new_bridge_does_not_adopt_a_running_keypad_recipe` (27 pass)
  - T1 retries with the latch: 11:01 started at once (vacuum already
    on) and no key was pressed, so not a valid T1; 11:05 nothing
    started (vacuum stayed off for 60 s). From now on each test starts
    only on the operator's go, after the operator has turned VACUUM on.
    T1 still open.
  - 11:07: with no bridge running the keypad's VACUUM key did nothing
    (expected in wiring B). Started `forward --seconds 600`
    (`sessions/20261117_110718_forward_between_tests/`) so the operator
    can switch VACUUM on before T1; on the operator's go, stop it and
    start T1.
  - 11:08 valid T1 with the latch: pass. Stop frame sent in the same
    poll as the key press; 493 to 31 rpm in 0.25 s, then 0 rpm while the
    keypad's own recipe ran (command up to 1209 rpm); latch released
    when the keypad went idle (`sessions/20261117_110816_abort_t1d_*`).
  - Started `forward --seconds 600` (`sessions/20261117_110930_forward_before_t2/`) so the
    operator can switch VACUUM on before T2.
  - 11:10 T2 pass: abort 0.50 s after the last keypad frame, 0 rpm
    0.30 s later (`sessions/20261117_111005_abort_t2_*`).
  - Started `forward --seconds 600` (`sessions/20261117_111117_forward_before_t3/`) before T3. T3
    uses `--min-vacuum 643`, just above the resting reading, so a real
    reading trips the check; no real leak is induced.
  - 11:11-11:13 T3 with `--min-vacuum 643`: twice cancelled in the
    countdown by a 642 reading (nothing turned); third try ran and
    stopped in the same poll as a 642 reading (1.19 s, 194 rpm). Pass.
  - User request: "642를 시작 기준으로 잡고 640을 정지기준으로 조정해서
    해줘". Added `run --start-vacuum` (default = `--min-vacuum`, must
    not be below it); `abort_test.sh` takes `START_VAC`. Repeat T3 with
    start 642 / stop 640.
  - User: "1번은 생략하고 2번부터 해보자": the T3 repeat at start
    642 / stop 640 is skipped; T3 stands on the 643 run above. Next:
    T4b (kill -9 at 300 rpm), then T4a.
  - 11:16 T4b: killed at 269-297 rpm; after 5 s with no frames the
    first mainboard reply read 0 rpm with vacuum held. The mainboard
    stops the spindle by itself when frames stop (time to stop within
    the 5 s not logged; asked the operator).
  - 11:23 T4a: abort 0.5 s after the last mainboard frame (284 rpm);
    on re-plug the mainboard read 0 rpm, vacuum 648. Operator: "잘
    멈추네". Like T4b, the mainboard stops the spindle by itself when
    frames stop and keeps the vacuum.
  - 11:30 final `run --rpm 2100 --accel 5 --hold 10` on the final code:
    2100 rpm command at 4.94 s, held 2093-2099 rpm for 9.96 s, 0 rpm
    0.43 s after the step, 0 bad frames. Pass.

## Web control (issue #6, branch `feature/web-control`)

### Background
Part 2 of the request above. User decisions: local network, FastAPI,
automated browser for the GUI check. Mid-task request: "웹사이트의
키패드 디자인은 실제 스핀코터의 UI 구성을 바탕으로 작업해줘".

### Tasks
- [x] PR #5 merged (abort tests T1, T2, T3, T4a, T4b and a final 2100 rpm
      run on the final code)
- [x] Issue #6; branch `feature/web-control`; `.venv` with FastAPI,
      uvicorn, httpx, Playwright + Chromium (ruff pinned to 0.15.9 like
      the hooks)
- [x] `Bridge.run_step(cancel=...)` and `last_sent_command`; test
- [x] `spincoater_midas/server.py`: controller thread, `GET /api/status`,
      `POST /api/run`, `POST /api/stop`, 3 s countdown, rpm limit 2100
- [x] `spincoater_midas/web/index.html`: copy of the real front panel
      (20x4 LCD, arrow keys, START/STOP, EDIT, VACUUM, ENTER, RCP SEL,
      PAUSE); EDIT/arrows/PAUSE/ENTER edit the web recipe; VACUUM is
      keypad-only by design
- [x] `tests/test_server.py` (8 tests; 36 in all pass; mutation-checked)
- [x] Server on the real cables, forwarding only; screenshots
- [x] Bench via the GUI: 2100 rpm / ACL 5 s / 10 s run started with the
      page's START/STOP; watch Set and Act on the page
- [x] Bench via the GUI: START/STOP pressed on the page mid-run
- [x] README section; commit; PR with evidence (PR #7)
  - 11:42 GUI run 2100/5/10: page Set 0 to 2100, Act to 2099-2100 rpm
    (99% at 5.16 s), held 10 s, END. Found: page Set stayed 2100 during
    the 0.5 s stop; fixed with `last_sent_command` = stop frame; test
    `test_last_sent_command_shows_the_stop` (fails without the fix).
  - 11:43 GUI stop test (fixed server) 1000 rpm: START/STOP on the page
    at 8.1 s, 999 to 0 rpm in 0.36 s, page Set 0 at once. Pass.
- [x] Before merging PR #7: open the page from another PC (needs the
      container's port 8000 published), and optionally repeat the
      2100 rpm GUI run on the fixed server; merge when the user asks
      (user: verify on this PC only; network access out of scope)

## Web control: this PC only, start order in the README example

### Background
User request (2026-11-17): "이 PC에서만 확인하는 것으로 하고 example에
서버랑 브릿지키는 방법과 순서도 정리해줘."

### Tasks
- [x] Server listens on 127.0.0.1 by default; `--host 0.0.0.0` stays
      as an untested option
- [x] Open the cables exclusively, so the bridge and the server (or two
      copies) cannot both drive the mainboard; check on the machine
- [x] README example: how and in which order to start the bridge or
      the server, with real output
- [x] Update PR #7 (drop the LAN item from the scope), merge
  - 11:47 checked on the machine: with the server running, identify
    showed both ports busy, bridge and a second server refused ("is in
    use"); after Ctrl+C the ports were free; forward 3 s, 0 bad frames
    (`sessions/20261117_114805_start_order/`).
