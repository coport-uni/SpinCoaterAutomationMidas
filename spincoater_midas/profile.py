"""Speed command for one recipe step, generated on the host.

The keypad does not send the set speed once; it ramps the command
itself during the acceleration time (ACL) and then holds it for the
step time. This module reproduces that so the host can stand in for
the keypad.
"""

from dataclasses import dataclass

# The keypad steps its command about every 100 ms (bench, 2026-11-17).
ramp_update_seconds = 0.1
# Guards against 0.3 / 0.1 evaluating to 2.9999.
tick_epsilon = 1e-9


@dataclass(frozen=True)
class StepProfile:
    """One recipe step: ramp to a speed, then hold it.

    Attributes:
        target_rpm: Speed to reach and hold.
        acceleration_seconds: Ramp time from 0 to ``target_rpm`` (ACL).
        hold_seconds: Time at ``target_rpm`` after the ramp. On this
            machine the step time counts from the end of the ramp.
    """

    target_rpm: int
    acceleration_seconds: float
    hold_seconds: float

    @property
    def total_seconds(self) -> float:
        """Time from START until the command returns to 0."""
        return self.acceleration_seconds + self.hold_seconds

    def command_at(self, elapsed: float) -> int:
        """Return the commanded speed a given time after START.

        The ramp rises in equal steps every ``ramp_update_seconds``. The
        first step is sent at START, as the keypad does, so the target is
        reached one update before the end of the acceleration time.

        Args:
            elapsed: Seconds since START.

        Returns:
            Commanded speed in rpm; 0 before START and after the step.
        """
        if elapsed < 0 or elapsed >= self.total_seconds:
            return 0
        ticks = round(self.acceleration_seconds / ramp_update_seconds)
        if ticks <= 0:
            return self.target_rpm
        tick = int(elapsed / ramp_update_seconds + tick_epsilon) + 1
        return self.target_rpm * min(tick, ticks) // ticks
