"""Frame format of the JP4 link between keypad and mainboard.

The keypad (MS-SN-KB12D) and the mainboard each stream one ASCII frame
about every 52 ms at 19200 bps. A frame is ``STX body checksum ETX``,
where the checksum is the byte sum of the body modulo 256, written as
two upper-case hex characters. Numeric fields are hex with the least
significant nibble first, so ``2D40`` means 0x04D2 = 1234.

The field layout was decoded from bench recordings on 2026-11-17; see
``docs/jp4_protocol.md`` for the evidence behind each field.

A keypad body is also a valid mainboard body (twelve hex characters),
so the direction of a frame must come from the wire it was read on.
"""

from dataclasses import dataclass

baud_rate = 19200
stx = 0x02
etx = 0x03
checksum_length = 2

# Keypad to mainboard: "C" + 11 characters.
keypad_command_letter = "C"
keypad_body_length = 12
keypad_prefix = "210"  # Constant in every recorded frame; meaning unknown.
keypad_tail = "000"  # Always zero so far; meaning unknown.
keypad_speed_slice = slice(4, 8)
keypad_flags_index = 8
flag_run = 0x1
flag_vacuum = 0x2

# Mainboard to keypad: 12 characters, no command letter.
mainboard_body_length = 12
mainboard_vacuum_slice = slice(0, 4)
mainboard_speed_slice = slice(4, 8)
mainboard_tail_slice = slice(8, 12)


class FrameError(ValueError):
    """A frame is malformed or fails its checksum."""


def compute_checksum(body: str) -> str:
    """Return the two-character checksum of a frame body.

    Args:
        body: Frame body between STX and the checksum.

    Returns:
        Byte sum of ``body`` modulo 256 as two upper-case hex characters.
    """
    return f"{sum(body.encode('ascii')) % 256:02X}"


def decode_hex_le(text: str) -> int:
    """Decode a hex field written least significant nibble first.

    Args:
        text: Hex characters, lowest nibble first, e.g. ``"2D40"``.

    Returns:
        The decoded integer, e.g. 1234.

    Raises:
        FrameError: If ``text`` contains a non-hex character.
    """
    try:
        return int(text[::-1], 16)
    except ValueError as error:
        raise FrameError(f"not a hex field: {text!r}") from error


def encode_hex_le(value: int, width: int) -> str:
    """Encode an integer as a hex field, least significant nibble first.

    Args:
        value: Non-negative integer to encode.
        width: Number of hex characters in the field.

    Returns:
        Upper-case hex text of exactly ``width`` characters.

    Raises:
        ValueError: If ``value`` is negative or does not fit ``width``.
    """
    if value < 0 or value >= 16**width:
        raise ValueError(f"{value} does not fit {width} hex digits")
    return f"{value:0{width}X}"[::-1]


def strip_frame(frame: bytes | str) -> str:
    """Check a frame's checksum and return its body.

    Args:
        frame: A frame with or without the STX/ETX bytes.

    Returns:
        The body without STX, checksum and ETX.

    Raises:
        FrameError: If the frame is not ASCII or the checksum is wrong.
    """
    if isinstance(frame, bytes):
        try:
            frame = frame.decode("ascii")
        except UnicodeDecodeError as error:
            raise FrameError(f"frame is not ASCII: {frame!r}") from error
    frame = frame.removeprefix(chr(stx)).removesuffix(chr(etx))
    body, checksum = frame[:-checksum_length], frame[-checksum_length:]
    if compute_checksum(body) != checksum.upper():
        raise FrameError(f"bad checksum in {frame!r}")
    return body


def wrap_frame(body: str) -> bytes:
    """Add checksum, STX and ETX to a body.

    Args:
        body: Frame body.

    Returns:
        The complete frame as bytes, ready to write to the port.
    """
    text = chr(stx) + body + compute_checksum(body) + chr(etx)
    return text.encode("ascii")


@dataclass(frozen=True)
class KeypadCommand:
    """One keypad frame: what the keypad asks the mainboard to do.

    Attributes:
        speed_rpm: Commanded spindle speed. The keypad ramps this value
            itself during acceleration.
        vacuum: True to hold the chuck vacuum on.
        run: True while a recipe step is running.
        prefix: Leading constant characters, kept for round-tripping.
        tail: Trailing characters, kept for round-tripping.
    """

    speed_rpm: int = 0
    vacuum: bool = False
    run: bool = False
    prefix: str = keypad_prefix
    tail: str = keypad_tail


@dataclass(frozen=True)
class MainboardStatus:
    """One mainboard frame: what the mainboard reports to the keypad.

    Attributes:
        vacuum_reading: Vacuum gauge value. The keypad LCD shows it as a
            negative number, e.g. 643 as ``Vac -642``.
        speed_rpm: Measured spindle speed.
        tail: Last four characters, always ``0000`` so far.
    """

    vacuum_reading: int
    speed_rpm: int
    tail: str


def parse_keypad_frame(frame: bytes | str) -> KeypadCommand:
    """Decode a keypad-to-mainboard frame.

    Args:
        frame: A frame with or without STX/ETX.

    Returns:
        The decoded command.

    Raises:
        FrameError: If the frame is malformed or fails its checksum.
    """
    body = strip_frame(frame)
    if len(body) != keypad_body_length or body[0] != keypad_command_letter:
        raise FrameError(f"not a keypad frame: {body!r}")
    flags = decode_hex_le(body[keypad_flags_index])
    return KeypadCommand(
        speed_rpm=decode_hex_le(body[keypad_speed_slice]),
        vacuum=bool(flags & flag_vacuum),
        run=bool(flags & flag_run),
        prefix=body[1 : keypad_speed_slice.start],
        tail=body[keypad_flags_index + 1 :],
    )


def build_keypad_frame(command: KeypadCommand) -> bytes:
    """Encode a keypad-to-mainboard frame.

    Args:
        command: The command to send.

    Returns:
        The complete frame as bytes, including STX, checksum and ETX.
    """
    speed_width = keypad_speed_slice.stop - keypad_speed_slice.start
    flags = (flag_vacuum if command.vacuum else 0) | (
        flag_run if command.run else 0
    )
    body = (
        keypad_command_letter
        + command.prefix
        + encode_hex_le(command.speed_rpm, speed_width)
        + encode_hex_le(flags, 1)
        + command.tail
    )
    if len(body) != keypad_body_length:
        raise ValueError(f"prefix or tail has the wrong length: {body!r}")
    return wrap_frame(body)


def parse_mainboard_frame(frame: bytes | str) -> MainboardStatus:
    """Decode a mainboard-to-keypad frame.

    Args:
        frame: A frame with or without STX/ETX.

    Returns:
        The decoded status.

    Raises:
        FrameError: If the frame is malformed or fails its checksum.
    """
    body = strip_frame(frame)
    if len(body) != mainboard_body_length:
        raise FrameError(f"not a mainboard frame: {body!r}")
    return MainboardStatus(
        vacuum_reading=decode_hex_le(body[mainboard_vacuum_slice]),
        speed_rpm=decode_hex_le(body[mainboard_speed_slice]),
        tail=body[mainboard_tail_slice],
    )


class FrameSplitter:
    """Cut a raw serial byte stream into STX..ETX frames.

    Bytes before the first STX and incomplete frames are held back until
    more data arrives, so ``feed`` can be called with any chunk size.
    """

    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        """Add received bytes and return every completed frame.

        Args:
            data: Bytes just read from the port.

        Returns:
            Completed frames without STX and ETX, oldest first.
        """
        self.buffer += data
        frames = []
        while True:
            start = self.buffer.find(stx)
            if start < 0:
                self.buffer.clear()
                return frames
            end = self.buffer.find(etx, start + 1)
            if end < 0:
                del self.buffer[:start]
                return frames
            frames.append(bytes(self.buffer[start + 1 : end]))
            del self.buffer[: end + 1]
