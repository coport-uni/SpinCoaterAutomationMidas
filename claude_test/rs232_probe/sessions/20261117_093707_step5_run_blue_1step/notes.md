# Session 09:37:07, one-step run, listening on Blue

Recipe A reduced to one step: 1234 rpm, step time 005.0 s, ACL 05.0 s.
Wafer on chuck. Operator pressed VACUUM, START, then VACUUM off.

- Frames: 1248 in 68.5 s, 0 bad checksums, no gaps, 52 distinct.
- 09:37:37.307 VACUUM on: `C21000002000` + `58`.
- 09:37:40.724 START: `C21081003000` + `62`; digits 4-7 `8100` -> 24,
  digit 8 `3` (vacuum + run).
- Command ramp in steps of 24-25 rpm about every 100 ms (each value
  sent twice) up to `2D40` -> 1234 at 09:37:45.607 (4.9 s).
- Held 1234 until 09:37:50.629, then `C21000002000` (speed 0, run off).
- 09:38:04.085 VACUUM off: `C21000000000` + `56`.
- START to end = 9.9 s = ACL 5 s + step 5 s.
- `lcd_run_keypoints.jpg`: LCD at 09:37:37.3, 09:37:40.7, 09:37:45.6,
  09:37:50.6 (STANDBY, STANDBY, RUN with ACL counting, RUN with Act
  time at 000.x).
