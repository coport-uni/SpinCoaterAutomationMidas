# JP4 Protocol Notes

Running notes on the serial link between the keypad board
(MS-SN-KB12D) and the mainboard. Wiring and voltages are in
[jp4_voltage_measurement.md](jp4_voltage_measurement.md); the front
panel layout is [front_panel_buttons.jpg](front_panel_buttons.jpg).

## Capture setup

| Item | Value |
|---|---|
| Adapter | KW-525 (Prolific PL-2303, `/dev/ttyUSB0`) |
| Tap | DB9 pin 2 (RXD) on JP4 **Blue**, pin 5 on Black |
| Camera | Logitech C920 (`/dev/video0`), aimed at the keypad LCD |
| Mode | Listen only. The host never writes to the port. |

## What is known (2026-11-17)

Evidence: `claude_test/rs232_probe/sweep_01.log` and
`claude_test/rs232_probe/frames_19200_idle.log`.

- **Line settings: 19200 bps, 8N1 (tentative).** Of 2400 to 115200 bps,
  only 19200 gives clean ASCII. The data so far is 7-bit ASCII, so
  even or odd parity has not been ruled out.
- **Direction: keypad to mainboard.** The tap is on Blue, which runs to
  SP3232 pin 14 (T1OUT).
- **Frame:**

  ```
  0x02 | 'C' | 11 ASCII digits  | 2 hex chars | 0x03
  STX  | cmd | 21000000000      | 56          | ETX
  ```

- **Checksum:** the byte sum of the command letter and the 11 digits,
  taken mod 256, written as two upper-case hex characters. Checked on
  the idle frame: `sum(b"C21000000000") % 256 == 0x56`.
- **Rate:** 19.2 frames per second (about every 52 ms), all identical
  in STANDBY. The keypad streams its state continuously rather than
  sending only on key presses.
- **Setpoints are not streamed in STANDBY.** Rpm, time and ACL were
  edited to 2200, 1234 rpm, 012.3 s and ACL 04.5 and shown on the LCD,
  but every frame stayed `C21000000000` + `56` (sessions 08:53:40 and
  08:58:06). The leading `210` is a constant, not the 2100 rpm
  setpoint; the speed only appears once START is pressed (see below).
- **Silent in EDIT mode:** the keypad sends nothing while EDIT mode is
  open (161.5 s gap, 08:54:00.9 to 08:56:42.4) and resumes on return
  to STANDBY. In EDIT mode the LCD hides the Act line and shows
  `Vac -300`, probably a vacuum threshold setting.
- **Digit 8 is the vacuum command.** It reads `2` while VACUUM is on
  and `0` while it is off: `C21000002000` + `58` vs. `C21000000000` +
  `56`. Three on/off cycles matched key presses on video, and the LCD
  Vac reading rose to about -160 while on (session 09:06:58).
- **Earlier unexplained change explained:** the `0` to `2` change seen
  between 08:50:43 and 08:51:15 (dry run) matches this vacuum flag; the
  LCD was not watched closely at that time.
- **Digit 8 is a bit field; START sets bit 0.** During a one-step run
  (session 09:37:07: 1234 rpm, step time 5.0 s, ACL 5.0 s, vacuum on)
  digit 8 read `3` = vacuum (2) + run (1).
- **Digits 4-7: commanded speed, hex, low nibble first.** `2D40` ->
  0x04D2 = 1234 rpm. The keypad generates the acceleration ramp itself:
  from START at 09:37:40.724 the command rose 24, 48, 72, ... in steps
  of 24-25 rpm about every 100 ms and reached 1234 at 09:37:45.607
  (4.9 s; ACL 5.0 s). It held 1234 until 09:37:50.629, then dropped
  straight to 0 with digit 8 back to `2`.
- **Step timing:** START to end took 9.9 s = ACL 5 s + step time 5 s,
  so the step time counts after the ramp. The LCD agrees: `ACL` counts
  down during the ramp, then `Act` counts the step time down to 000.x.

Keypad frame layout (digit positions after the command letter `C`):

| Digits | Idle value | Meaning |
|---|---|---|
| 1-3 | `210` | Constant in every frame so far. Meaning unknown. |
| 4-7 | `0000` | Commanded speed in rpm, 4 hex nibbles, low nibble first. |
| 8 | `0` | Flags: bit 1 (`2`) = vacuum on, bit 0 (`1`) = run. |
| 9-11 | `000` | Unknown, always `0` so far. |

Worked example, mid-run frame `C2102D40300073`:

```
C | 210 | 2D40 -> 0x04D2 = 1234 rpm | 3 = vacuum + run | 000 | 73
```

`sum(b"C2102D403000") % 256 == 0x73` (the 11 digits plus `C`).

## Mainboard to keypad (White)

Evidence: `claude_test/rs232_probe/sweep_02_white.log` and
`claude_test/rs232_probe/sessions/20261117_091549_phaseB_white_idle_vacuum/`.

- **Line settings:** 19200 bps, same as Blue. About 19 frames per
  second, sent continuously.
- **Frame:** no command letter, 12 characters, same checksum rule
  (byte sum mod 256 in hex). Idle: `000000000000` + `40`.

  ```
  0x02 | 12 characters | 2 hex chars | 0x03
  STX  | 000000000000  | 40          | ETX
  ```

- **Characters 1-2: vacuum reading, hex, low nibble first.** `7A`
  decodes to 0xA7 = 167. During three vacuum-on periods the value rose
  10, 78, 103, 130, 151 and held at 144-175, and returned to 0 when
  vacuum was switched off. The LCD showed `Vac -163` at three moments
  where the decoded mean over +-0.5 s was 162.6, 163.7 and 164.2, so
  the keypad displays a smoothed version of this value as a negative
  number. Whether the field is wider than two characters (values above
  255) is not known yet.
- **The vacuum field is at least three characters wide.** With a wafer
  on the chuck the reading was `382` -> 0x283 = 643 (LCD `Vac -642`),
  so characters 1-3 (likely 1-4) form one little-endian hex field.
- **Characters 5-7: speed, hex, low nibble first** (session 09:27:08).
  `0D4` -> 0x4D0 = 1232 with Set 1234 rpm. The ramp went from 0 to
  1233 in 4.9 s with ACL 5.0 s, and the LCD read `Act 0783rpm` when the
  field read 793. Characters 8-12 stayed `0`.
- **Unresolved:** steps 2-5 of the recipe ran with `Set 0000rpm`. The
  speed field held 1230-1234 for 55.7 s while the LCD showed
  `Act 0246rpm` (1232 / 5 = 246.4). At END the field fell
  1232 -> 669 -> 3 -> 0 within 0.26 s. The operator saw the chuck keep
  spinning at a similar speed through steps 2-5, so the mainboard field
  is taken as the real speed and the LCD `Act 0246rpm` as wrong or
  meaning something else. A step with `Set 0000rpm` therefore appears
  to hold the previous speed rather than stop.

| Characters | Meaning |
|---|---|
| 1-4 | Vacuum reading (likely 4 hex nibbles, low first; 4 was always 0) |
| 5-8 | Speed in rpm (likely 4 hex nibbles, low first; 8 was always 0) |
| 9-12 | Unknown, always `0` so far |

## Measurement plan

The goal is to map every field and command letter, in both directions,
to a front panel action. Each step changes one thing and is recorded
with a timestamped frame log plus a webcam snapshot of the LCD each
time the frame content changes.

### Phase A: keypad to mainboard (tap on Blue, current wiring)

1. **Idle baseline.** Done: `C21000000000` + `56`.
2. **Setpoint edits, motor stopped.** With EDIT, change one value at a
   time and save with ENTER: rpm (2100 to 2200 to 2101), time
   (015.0 to 016.0), ACL (00.0 to 01.0). This finds which digits each
   value moves and whether the stream follows the edit cursor or only
   the saved value.
3. **Recipe and step selection.** RCP SEL and step changes (Stp01 to
   Stp02) to see whether the stream follows the selected step.
4. **VACUUM on and off**, no wafer needed. Looks for a flag digit or a
   new command letter.
5. **Spin run, operator present.** A one-step recipe at low rpm
   (for example 500 rpm, 5 s), empty chuck, lid closed, e-stop within
   reach. Then START/STOP and PAUSE mid-run. This shows the run
   command and whether the setpoint streams during acceleration.
   The operator starts the run; the host only listens.

### Phase B: mainboard to keypad (move the tap to White)

Move DB9 pin 2 from Blue to White, or add a second KW-525, and repeat
steps 1, 4 and 5. The LCD values `Act ... rpm` and `Vac -000` must come
from this direction, so the frames should change with real speed and
vacuum.

### Phase C: decide and test transmission

After both directions are mapped, the host transmits only with the
keypad disconnected and the operator present, starting with the idle
frame and a stopped motor (Stage 3 in `ToDo.md`).

## Open questions

- Meaning of the eight zero digits and of command letters other
  than `C`.
- Parity: 8N1 vs. 8E1/8O1. A frame with a byte above 0x7F, or a scope
  trace, will settle it.
- Whether the mainboard acknowledges each frame or streams on its own.
