# JP4 Voltage Measurement

JP4 is the four-wire header that joins the keypad board (MS-SN-KB12D)
to the mainboard. The operator measured the DC voltage between every
pair of its wires with a multimeter on 2026-11-17, with the machine
powered and the cable connected. The handwritten sheet is
[jp4_voltage_matrix.jpg](jp4_voltage_matrix.jpg) (rotated 90 degrees).

## Raw readings

Voltage magnitude in volts between each pair of wires. The sheet does
not record polarity.

|           | Red | White | Blue | Black |
|-----------|-----|-------|------|-------|
| **Red**   | 0   | 9.3   | 9.4  | 5     |
| **White** | 9.3 | 0     | 0.1  | 4.3   |
| **Blue**  | 9.4 | 0.1   | 0    | 4.4   |
| **Black** | 5   | 4.3   | 4.4  | 0     |

The White/Black cell was first written as 4.7 and corrected to 4.3 on
the sheet; 4.3 matches the Black/White cell.

## Interpretation

Taking Black as 0 V and Red as +5 V, the matrix is fully consistent
only if White and Blue sit **below** ground:

| Wire  | Potential vs. Black | Inferred role                     |
|-------|---------------------|-----------------------------------|
| Red   | +5.0 V              | VCC                               |
| Black | 0 V                 | GND                               |
| White | about -4.3 V        | RS-232 data line, idle (mark)     |
| Blue  | about -4.4 V        | RS-232 data line, idle (mark)     |

Check: Red-White = 5.0 + 4.3 = 9.3 V, Red-Blue = 5.0 + 4.4 = 9.4 V,
White-Blue = 0.1 V. All three match the readings.

This supports the hypothesis from the chip photographs: the SP3232EEA
drives an RS-232 link, and an idle RS-232 line rests at a negative
voltage. Both data lines are near -4.4 V, so each one is driven by a
transmitter -- one on the keypad side and one on the mainboard side.
An undriven SP3232 receiver input would read close to 0 V instead.

The readings are close to the full idle level, which suggests the link
is mostly quiet rather than streaming continuously. A multimeter
averages, so this is a hint, not a measurement of traffic.

## Polarity check

The operator re-measured each wire with the black probe on Black
(2026-11-17) and reported that Red is positive and White and Blue are
negative, as predicted above. The role assignment therefore holds.

## Direction

With power off, the operator found continuity between **Blue** and
SP3232 pin 14 (T1OUT) on the keypad board (2026-11-17). Blue therefore
carries data from the keypad to the mainboard.

| Wire  | SP3232 pin      | Direction          |
|-------|-----------------|--------------------|
| Blue  | 14 (T1OUT)      | keypad -> mainboard |
| White | 13 (R1IN), expected | mainboard -> keypad |

White has not been checked against pin 13 yet; it is the only
remaining data wire, so pin 13 is expected.

## Still unconfirmed

- **White to pin 13.** Confirm continuity between White and SP3232
  pin 13 (R1IN).
- **Baud rate and framing.** Needs a logic analyzer on the TTL side of
  the SP3232 (Stage 1 of the plan in `ToDo.md`).
