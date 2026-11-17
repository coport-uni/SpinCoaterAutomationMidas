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
- [ ] Commit on `feature/jp4-protocol-parser`, push, open PR, merge
- [ ] New branch for the bridge; write the forward/override program
- [ ] Bench test with the operator: forwarding only, then the 2100 rpm
      scenario
