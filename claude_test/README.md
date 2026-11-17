# claude_test

Debug scripts and one-off experiments. Not part of CI.

| File | What it does | What was learned |
|---|---|---|
| `rs232_probe/baud_sweep.py` | Listen-only sweep of common baud rates on the KW-525 (`/dev/ttyUSB0`). Never writes to the port. | Only 19200 bps gives clean frames on JP4 Blue: `STX C 21000000000 56 ETX`. |
| `rs232_probe/sweep_01.log` | Output of the first sweep, machine in STANDBY. | 2400-115200 tried; 19200 is the only readable rate. |
| `rs232_probe/frames_19200_idle.log` | 10 s capture at 19200, frames grouped. | 192 identical frames, 19.2 per second; tail is a mod-256 byte-sum checksum in hex ASCII. |
| `rs232_probe/cam_standby.jpg` | Logitech C920 frame taken during the capture. | Webcam works and shows the keypad LCD (Set 2100 rpm). |
| `rs232_probe/capture_session.py` | Listen-only session recorder: logs every frame with wall-clock time (`frames.csv`), logs content changes (`changes.log`) with a webcam snapshot each, and records the webcam with a time overlay (`video.mp4`, not committed). | Camera pinned to 15 fps; the file is retimed to the measured rate so playback matches real time. |
| `rs232_probe/sessions/` | One folder per recording session. | Dry run 08:51:15: digit 8 changed `0` to `2` with no LCD change. |
| `rs232_probe/sessions/20261117_085340_step2_setpoint_edits/` | Step 2 session: EDIT, rpm edits, exit. `notes.md` and two contact sheets. | Keypad is silent in EDIT mode; after exit LCD showed 2200 rpm but frames still said 2100. |
| `rs232_probe/sessions/20261117_085806_step2b_one_edit_per_visit/` | Step 2b: one edit per EDIT visit, 10 s in STANDBY after each. `notes.md`, `sheet_standby_windows.jpg`. | LCD showed 1234 rpm, 012.3 s, ACL 04.5 in turn; frames never changed. Setpoints are not streamed in STANDBY. |
| `rs232_probe/sessions/20261117_090658_step4_vacuum_blue/` | Step 4: VACUUM on/off three times on Blue, pin 3 disconnected. `notes.md`, `sheet_vacuum_changes.jpg`. | Digit 8 = vacuum command (`2` on, `0` off). |
| `rs232_probe/sweep_02_white.log` | Baud sweep with DB9 pin 2 on JP4 White (mainboard to keypad). | 19200 bps again; frame `STX 000000000000 40 ETX`, 12 digits, no command letter. |
| `rs232_probe/sessions/20261117_091549_phaseB_white_idle_vacuum/` | Phase B on White: idle and three VACUUM cycles. `notes.md`, `lcd_vac_check.jpg`. | Characters 1-2 = vacuum reading, hex low nibble first; mean matches LCD `Vac -163`. |
| `rs232_probe/sessions/20261117_092708_step5_run_white/` | First run (5 steps ran by accident), listening on White. `notes.md`, `lcd_run_sequence.jpg`. | Characters 5-7 = speed, hex low nibble first; ramp matches ACL 5 s. Steps 2-5: field 1232 vs LCD 246, unresolved. |
| `rs232_probe/sessions/20261117_093707_step5_run_blue_1step/` | One-step run (1234 rpm, 5 s, ACL 5 s), listening on Blue. `notes.md`, `lcd_run_keypoints.jpg`. | Digits 4-7 = commanded speed (hex low nibble first); digit 8 bit 0 = run; keypad ramps the command in ~24 rpm steps every 100 ms. |
| `rs232_probe/sessions/.gitignore` | Keeps session videos (`*.mp4`) and per-change snapshots (`changes/`) out of git; logs, notes and curated sheets are committed. | Raw videos are 80-130 MB; White-wire sessions made 753 and 909 snapshots (about 480 MB in all). Curated stills and H.264 videos live in `docs/media/`. |
| `rs232_probe/sessions/20261117_085115_dryrun/` | 10 s dry run of `capture_session.py` after the snapshot and frame-rate fixes. | 180 frames, 0 bad checksums; digit 8 read `2`, later explained as VACUUM on. |
| `readme_figures/make_figures.py` | Draws `docs/diagrams/*.png` (frame anatomy, run speed/vacuum chart, wiring B, DB9 faces) from the session recordings. Needs matplotlib (installed in a scratch venv, not a project dependency). | Measured speed tracks the keypad command within a few rpm; vacuum 643 with wafer vs 163 empty. |
