# Media Index

Webcam recordings and stills from the bench, kept for the project
README. All webcam footage is a Logitech C920 aimed at the keypad
board (MS-SN-KB12D), recorded by
`claude_test/rs232_probe/capture_session.py` with a wall-clock overlay
in the top-left corner. Times are local (KST) on 2026-11-17.

The full-quality originals (MPEG-4 Part 2, 83 MB and 131 MB) stay in
the session folders under `claude_test/rs232_probe/sessions/` and are
not committed; the copies here are H.264 re-encodes (CRF 28, 720p,
15 fps) of the same footage.

## Videos

| File | Length | What it shows | Frame log |
|---|---|---|---|
| [videos/20261117_0853_edit_mode_silence.mp4](videos/20261117_0853_edit_mode_silence.mp4) | 3 min 17 s | EDIT pressed at 08:54:00; the keypad stops sending until STANDBY returns at 08:56:42. LCD ends at 2200 rpm. | `sessions/20261117_085340_step2_setpoint_edits/` |
| [videos/20261117_0858_setpoint_edits.mp4](videos/20261117_0858_setpoint_edits.mp4) | 5 min 28 s | One edit per EDIT visit: 2200 to 1234 rpm, 012.3 s, ACL 04.5, then back to 2100 rpm, 015.0 s, ACL 00.0. Frames stay `C21000000000` + `56` throughout. | `sessions/20261117_085806_step2b_one_edit_per_visit/` |
| [videos/20261117_0858_setpoint_edits_timelapse.gif](videos/20261117_0858_setpoint_edits_timelapse.gif) | 27 s (12x) | Same session, cropped to the board, for embedding in a README. | as above |
| [videos/20261117_0906_vacuum_toggle.mp4](videos/20261117_0906_vacuum_toggle.mp4) | 3 min 17 s | VACUUM on/off three times (09:08:34 to 09:10:01); digit 8 of the frame toggles `0`/`2` with each press. | `sessions/20261117_090658_step4_vacuum_blue/` |
| [videos/20261117_0915_white_vacuum_reading.mp4](videos/20261117_0915_white_vacuum_reading.mp4) | 2 min 7 s | Listening on White: three VACUUM cycles; LCD `Vac -163` matches the mainboard's vacuum field. | `sessions/20261117_091549_phaseB_white_idle_vacuum/` |
| [videos/20261117_0927_run_5steps_white.mp4](videos/20261117_0927_run_5steps_white.mp4) | 2 min 42 s | First run: step 1 at 1234 rpm then steps 2-5 by accident; listening on White. | `sessions/20261117_092708_step5_run_white/` |
| [videos/20261117_0937_run_1step_blue.mp4](videos/20261117_0937_run_1step_blue.mp4) | 1 min 6 s | One-step run (1234 rpm, 5 s, ACL 5 s), listening on Blue: the keypad's commanded speed ramps 24 -> 1234. | `sessions/20261117_093707_step5_run_blue_1step/` |

## Images

| File | What it shows |
|---|---|
| [images/webcam_first_frame_standby.jpg](images/webcam_first_frame_standby.jpg) | First webcam frame (08:39), keypad LCD in STANDBY at 2100 rpm. |
| [images/webcam_view_keypad_buttons.jpg](images/webcam_view_keypad_buttons.jpg) | Final camera angle: LCD and all ten buttons in frame. |
| [images/edit_mode_enter_sheet.jpg](images/edit_mode_enter_sheet.jpg) | 08:53:58 to 08:54:04 at 2 fps: EDIT pressed, LCD switches to `EDIT Stp01`, Act line blank, `Vac -300`. |
| [images/edit_mode_exit_sheet.jpg](images/edit_mode_exit_sheet.jpg) | 08:56:39 to 08:56:44 at 2 fps: leaving EDIT, LCD back to STANDBY at 2200 rpm. |
| [images/setpoint_edits_lcd_sequence.jpg](images/setpoint_edits_lcd_sequence.jpg) | LCD in STANDBY after each edit, top to bottom: 2200 rpm, 1234 rpm, 012.3 s, ACL 04.5, restored. |
| [images/vacuum_toggle_changes_sheet.jpg](images/vacuum_toggle_changes_sheet.jpg) | Snapshot at each frame change in the VACUUM session (09:06:58): finger on VACUUM each time; Vac -162 / -160 at OFF. |
| [images/white_vacuum_lcd_163.jpg](images/white_vacuum_lcd_163.jpg) | LCD `Vac -163` at 09:16:30, 09:16:55 and 09:17:29; decoded means 162.6, 163.7, 164.2. |
| [images/run_lcd_sequence_5steps.jpg](images/run_lcd_sequence_5steps.jpg) | LCD through the first run: STANDBY, RUN Stp01 (Act 0783), Stp02-05 (Set 0000, Act 0246), END. |
| [images/run_blue_lcd_keypoints.jpg](images/run_blue_lcd_keypoints.jpg) | LCD at VACUUM on, START, end of ramp and end of step in the one-step run. |

## Other photos in `docs/`

| File | What it shows |
|---|---|
| [../front_panel_buttons.jpg](../front_panel_buttons.jpg) | Machine front panel and the detached keypad board. |
| [../jp4_voltage_matrix.jpg](../jp4_voltage_matrix.jpg) | Handwritten JP4 pairwise voltage sheet. |
| `../KakaoTalk_20261117_162441136*.jpg` | Close-ups of the keypad board chips (ATmega128A, SP3232EEA, 24LC256) and JP3/JP4. |
| [../diagrams/db9_pinout.svg](../diagrams/db9_pinout.svg) | KW-525 DB9 pin faces and wiring table. |
