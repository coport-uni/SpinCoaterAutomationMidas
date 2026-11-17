# Session 09:15:49, Phase B (White, mainboard to keypad), VACUUM

- Frames: 2407 in 129.8 s, 0 bad checksums, 35 distinct, no gaps.
- Idle frame: `000000000000` + `40` (12 characters, no command letter).
- Only characters 1-2 ever change; characters 3-12 stayed `0`.
- Characters 1-2 are a hex byte written low nibble first:
  `7A` -> 0xA7 = 167, `F9` -> 0x9F = 159.
- Three vacuum-on periods: 09:16:18.8-09:16:36.3, 09:16:48.6-09:17:00.9,
  09:17:17.4-09:17:36.6. Value rises 10, 78, 103, 130, 151 ... and
  holds at 144-175; drops to 0 when vacuum is switched off.
- LCD check (`lcd_vac_check.jpg`): LCD read `Vac -163` at 09:16:30.650,
  09:16:55.655 and 09:17:29.657. Decoded means over +-0.5 s: 162.6,
  163.7, 164.2.
