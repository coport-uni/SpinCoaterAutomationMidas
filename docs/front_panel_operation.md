# Front Panel Operation

How the SPIN-1200D front panel is operated, collected while
reverse-engineering the keypad link. The button layout is in
[front_panel_buttons.jpg](front_panel_buttons.jpg).

| Group | Buttons |
|---|---|
| Right block, 2 columns x 3 rows | START/STOP, EDIT; VACUUM, ENTER; RCP SEL (skip), PAUSE (digit sel) |
| Arrow keys | Left, Up, Down, Right |

## Source and status

The procedures below come from fragments of the English SPIN-1200D user
manual on manualzz
(https://manualzz.com/doc/24803525/1200d-%EC%98%81%EB%AC%B8). The full
page could not be retrieved here (HTTP 403), so the wording is
incomplete. Check the original before relying on an exact sequence.
Each item says whether it was seen on this machine.

## Delete a step

From the manual excerpt:

1. Press Up or Down to move from `Stp01` to the step to delete.
2. Hold VACUUM and press Down.
3. Press Right to delete the step.

Later steps move up by one automatically. Whether this is done inside
EDIT mode is not stated in the excerpt.

On this machine (2026-11-17) the operator reduced recipe A from five
steps (`Stp01/05`) to one (`Stp01/01`). The exact key sequence used was
not recorded.

## Insert a step

The manual calls this "additional insertion of STEP". Inserting a step
shifts every following step down by one. To reorder steps, delete the
step and insert a new one at the target position with the same values.
The key sequence was not captured in the excerpt.

## Edit a value

- EDIT enters edit mode. The keypad stops transmitting on JP4 while
  edit mode is open (seen on this machine, see `jp4_protocol.md`).
- PAUSE (digit sel) selects the digit to change; Up and Down change it.
- ENTER stores the value.

## RCP SEL (skip)

- In STANDBY it selects one of up to 20 recipes (spec: 20 recipes,
  50 steps).
- While a recipe is running it skips the current step. The manual has a
  caution about using skip on each step, but the excerpt is cut off;
  read the full text before using it.

## LCD fields seen on this machine

```
STANDBY Stp01/05 V A     state, step n of total, V = vacuum on, recipe A
Set 015.0    2100rpm     step time (s), set speed
Act   0.0       0rpm     elapsed time, actual speed (see note)
ACL00.0sec  Vac -000     acceleration time, vacuum reading
```

- States seen: `STANDBY`, `EDIT`, `RUN`, `END`.
- `V` appears next to the recipe letter while VACUUM is on.
- In EDIT mode the Act line is blank and `Vac -300` is shown, probably
  the vacuum threshold.
- **Note on Act rpm:** during steps 2-5 of the first run (`Set 0000rpm`)
  the LCD showed `Act 0246rpm`, but the mainboard reported about
  1232 rpm and the operator saw the chuck keep spinning at a similar
  speed. Treat the LCD Act value as unreliable in that case.
