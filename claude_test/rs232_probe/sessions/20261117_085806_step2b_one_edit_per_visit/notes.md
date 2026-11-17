# Session 08:58:06, step 2b (one edit per EDIT visit)

- Frames: 3963 in 331 s, 0 bad checksums, all `C2100000000056`.
- Four silent gaps, one per EDIT visit:
  09:00:08.9-09:00:34.7, 09:00:55.4-09:01:18.0,
  09:01:42.4-09:02:07.4, 09:02:26.9-09:03:16.0.
- LCD in STANDBY between visits (`sheet_standby_windows.jpg`, top to
  bottom): 2200 rpm / 015.0 s / ACL 00.0 -> 1234 rpm -> 012.3 s ->
  ACL 04.5 -> restored 2100 rpm / 015.0 s / ACL 00.0.
- Conclusion: in STANDBY the stream does not carry rpm, time or ACL
  setpoints. `2100` in the frame matched the original setpoint by
  coincidence or is updated only by another event (START is the next
  candidate).
