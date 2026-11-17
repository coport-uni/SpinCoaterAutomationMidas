# Session 09:27:08, step 5 run, listening on White

Recipe as run: step 1 = 1234 rpm, 005.0 s, ACL 05.0 s; steps 2-5 also
ran (Set 0000 rpm; times 13.0, ?, 14.0, 12.0 s, ACL 00.0/00.0/00.0/07.0
as read from the LCD). Wafer on chuck, VACUUM on before START.

- Frames: 3046 in 162 s, 0 bad checksums, no gaps.
- Characters 1-3: vacuum, hex low nibble first (`382` -> 0x283 = 643);
  LCD `Vac -642`/`-643` throughout. Character 4 always 0.
- Characters 5-7: speed, hex low nibble first (`0D4` -> 0x4D0 = 1232).
  Character 8 always 0. Characters 9-12 always 0.
- Ramp: 0 at 09:28:27.876, 29 at 09:28:27.927, 1233 at 09:28:32.849
  (4.9 s; ACL 5.0 s). LCD `Act 0783rpm` at 09:28:31.128, field 793.
- Steps 2-5 (09:28:33 to 09:29:28.7, 55.7 s): field held 1230-1234;
  LCD showed `Set 0000rpm`, `Act 0246rpm`. Unresolved; 1232 / 5 = 246.4.
- END: field 1232 -> 669 -> 3 -> 0 between 09:29:28.703 and
  09:29:28.959. LCD `END Stp06/05`, Act 0000 rpm.
- `lcd_run_sequence.jpg`: LCD at 09:28:19, :31, :39, :49, 09:29:04, :19, :29.
