# Draws the README figures from the recorded sessions; rerun after new recordings. Needs matplotlib.
import csv
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.lines  # noqa: E402
import matplotlib.patches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.text  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Polygon  # noqa: E402

repo = pathlib.Path(__file__).resolve().parents[2]
sessions = repo / "claude_test" / "rs232_probe" / "sessions"
out_dir = repo / "docs" / "diagrams"

# Reference palette (dataviz skill, light mode).
surface = "#fcfcfb"
ink = "#0b0b0b"
ink_muted = "#52514e"
grid = "#e4e3df"
series_blue = "#2a78d6"
series_orange = "#eb6834"
wire = {
    "red": "#d23b2e",
    "black": "#1d1d1b",
    "white": "#b9b8b2",
    "blue": "#2a78d6",
}
box_fill = "#f1f0ec"
box_edge = "#8a8983"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.edgecolor": box_edge,
        "axes.labelcolor": ink_muted,
        "xtick.color": ink_muted,
        "ytick.color": ink_muted,
        "figure.facecolor": surface,
        "axes.facecolor": surface,
        "savefig.facecolor": surface,
    }
)


def seconds(text):
    hours, minutes, secs = text.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(secs)


def load(session):
    with open(sessions / session / "frames.csv", newline="") as handle:
        return [
            (seconds(r["time"]), r["frame"]) for r in csv.DictReader(handle)
        ]


def hex_le(text):
    return int(text[::-1], 16)


def frame_anatomy():
    fig, ax = plt.subplots(figsize=(12, 6.2))
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 62)
    ax.axis("off")

    def row(y, title, cells, notes):
        ax.text(1, y + 11, title, fontsize=13, fontweight="bold", color=ink)
        x = 1
        for (text, width, color), note in zip(cells, notes):
            ax.add_patch(
                FancyBboxPatch(
                    (x, y),
                    width - 0.6,
                    7,
                    boxstyle="round,pad=0,rounding_size=0.8",
                    facecolor=color,
                    edgecolor=box_edge,
                    linewidth=1,
                )
            )
            ax.text(
                x + (width - 0.6) / 2,
                y + 3.5,
                text,
                ha="center",
                va="center",
                fontsize=15,
                family="DejaVu Sans Mono",
                fontweight="bold",
                color=ink,
            )
            ax.text(
                x + (width - 0.6) / 2,
                y - 1.5,
                note,
                ha="center",
                va="top",
                fontsize=9.5,
                color=ink_muted,
                linespacing=1.3,
            )
            x += width

    plain = box_fill
    speed = "#d6e6f8"
    flags = "#fbe0d4"
    vacuum = "#d3f0e4"
    check = "#ecebe6"
    row(
        40,
        "Keypad → mainboard (Blue wire), mid-run",
        [
            ("STX", 8, plain),
            ("C", 7, plain),
            ("210", 14, plain),
            ("2D40", 22, speed),
            ("3", 22, flags),
            ("000", 14, plain),
            ("73", 18, check),
            ("ETX", 8, plain),
        ],
        [
            "0x02",
            "command",
            "constant\n(meaning\nunknown)",
            "commanded speed\n0x04D2 = 1234 rpm",
            "flags: 3 =\nvacuum (2) + run (1)",
            "unused\nso far",
            "checksum\nsum mod 256",
            "0x03",
        ],
    )
    row(
        12,
        "Mainboard → keypad (White wire), same set speed",
        [
            ("STX", 8, plain),
            ("3820", 21, vacuum),
            ("0D40", 21, speed),
            ("0000", 18, plain),
            ("65", 18, check),
            ("ETX", 8, plain),
        ],
        [
            "0x02",
            "vacuum reading\n0x0283 = 643\n(LCD: Vac -642)",
            "measured speed\n0x04D0 = 1232 rpm",
            "unused\nso far",
            "checksum\nsum mod 256",
            "0x03",
        ],
    )
    ax.text(
        119,
        60,
        "Hex fields are written lowest digit first:\nread them right to left.  2D40 → 04D2 = 1234",
        ha="right",
        va="top",
        fontsize=10.5,
        color=ink,
        bbox={
            "boxstyle": "round,pad=0.5",
            "facecolor": "#fff8e6",
            "edgecolor": "#eda100",
        },
    )
    return fig


def run_profile():
    keypad = load("20261117_093707_step5_run_blue_1step")
    mainboard = load("20261117_092708_step5_run_white")
    vacuum_empty = load("20261117_091549_phaseB_white_idle_vacuum")

    command = [(t, hex_le(f[4:8])) for t, f in keypad]
    keypad_start = next(t for t, f in keypad if int(f[8], 16) & 1)
    measured = [(t, hex_le(f[4:8])) for t, f in mainboard]
    measured_start = next(t for t, v in measured if v > 0)

    fig, (top, bottom) = plt.subplots(
        2, 1, figsize=(10, 8.4), gridspec_kw={"hspace": 0.55}
    )
    window = 11.0
    top.axvspan(0, 5, color="#eef4fc", zorder=0, gid="background")
    top.axvspan(5, 10, color="#f6f5f1", zorder=0, gid="background")
    top.text(
        2.9,
        60,
        "ACL 5.0 s\nkeypad ramps the command",
        ha="left",
        va="bottom",
        fontsize=9.5,
        color=ink_muted,
    )
    top.text(
        6.0,
        60,
        "step time 5.0 s\nat set speed",
        ha="left",
        va="bottom",
        fontsize=9.5,
        color=ink_muted,
    )
    xs = [
        t - keypad_start
        for t, _ in command
        if -0.5 <= t - keypad_start <= window
    ]
    ys = [v for t, v in command if -0.5 <= t - keypad_start <= window]
    top.step(
        xs,
        ys,
        where="post",
        color=series_blue,
        linewidth=2,
        label="Commanded by keypad (Blue wire, run at 09:37)",
    )
    xs = [
        t - measured_start
        for t, _ in measured
        if -0.5 <= t - measured_start <= window
    ]
    ys = [v for t, v in measured if -0.5 <= t - measured_start <= window]
    top.plot(
        xs,
        ys,
        color=series_orange,
        linewidth=2,
        label="Measured by mainboard (White wire, run at 09:28)",
    )
    top.set_xlim(-0.5, window)
    top.set_ylim(0, 1600)
    top.set_xlabel("Seconds since START")
    top.set_ylabel("Speed (rpm)")
    top.set_title(
        "Recipe step: 1234 rpm, ACL 5.0 s, step 5.0 s",
        loc="left",
        fontsize=12.5,
        color=ink,
        pad=34,
    )
    top.grid(axis="y", color=grid, linewidth=0.8)
    top.legend(
        loc="upper left",
        bbox_to_anchor=(0, 1.2),
        ncol=2,
        frameon=False,
        fontsize=10,
    )
    top.annotate(
        "command drops to 0\nat 9.9 s",
        xy=(9.9, 600),
        xytext=(7.2, 800),
        fontsize=9.5,
        color=ink_muted,
        arrowprops={"arrowstyle": "->", "color": ink_muted},
    )
    top.annotate(
        "measured run kept spinning:\nits recipe still had steps 2-5",
        xy=(10.6, 1250),
        xytext=(7.6, 1330),
        fontsize=9.0,
        color=ink_muted,
        ha="right",
        va="bottom",
        arrowprops={"arrowstyle": "->", "color": ink_muted},
    )
    for side in ("top", "right"):
        top.spines[side].set_visible(False)

    empty = [(t, hex_le(f[0:4])) for t, f in vacuum_empty if f and len(f) >= 14]
    empty_on = next(t for t, v in empty if v > 0)
    empty_off = next(t for t, v in empty if t > empty_on + 1 and v == 0)
    wafer = [(t, hex_le(f[0:4])) for t, f in mainboard]
    wafer_on = next(t for t, v in wafer if v > 0)
    span = 16.0
    bottom.plot(
        [t - wafer_on for t, v in wafer if 0 <= t - wafer_on <= span],
        [v for t, v in wafer if 0 <= t - wafer_on <= span],
        color=series_blue,
        linewidth=2,
        label="Wafer on chuck",
    )
    bottom.plot(
        [
            t - empty_on
            for t, v in empty
            if 0 <= t - empty_on <= min(span, empty_off - empty_on - 0.1)
        ],
        [
            v
            for t, v in empty
            if 0 <= t - empty_on <= min(span, empty_off - empty_on - 0.1)
        ],
        color=series_orange,
        linewidth=2,
        label="Empty chuck",
    )
    bottom.axhline(163, color=ink_muted, linewidth=1, linestyle=(0, (4, 3)))
    bottom.text(
        span,
        200,
        "LCD showed Vac -163 (dashed)",
        ha="right",
        va="bottom",
        fontsize=9.5,
        color=ink_muted,
    )
    bottom.axhline(642, color=ink_muted, linewidth=1, linestyle=(0, (4, 3)))
    bottom.text(
        span,
        670,
        "LCD showed Vac -642 (dashed)",
        ha="right",
        va="bottom",
        fontsize=9.5,
        color=ink_muted,
    )
    bottom.set_xlim(0, span)
    bottom.set_ylim(0, 760)
    bottom.set_xlabel("Seconds since VACUUM pressed")
    bottom.set_ylabel("Vacuum reading")
    bottom.set_title(
        "Vacuum reading reported by the mainboard",
        loc="left",
        fontsize=12.5,
        color=ink,
        pad=34,
    )
    bottom.grid(axis="y", color=grid, linewidth=0.8)
    bottom.legend(
        loc="upper left",
        bbox_to_anchor=(0, 1.2),
        ncol=2,
        frameon=False,
        fontsize=10,
    )
    for side in ("top", "right"):
        bottom.spines[side].set_visible(False)
    return fig


def box(ax, x, y, w, h, title, subtitle="", fill=box_fill):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0,rounding_size=1.2",
            facecolor=fill,
            edgecolor=box_edge,
            linewidth=1.2,
        )
    )
    ax.text(
        x + w / 2,
        y + h / 2 + (1.6 if subtitle else 0),
        title,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=ink,
    )
    if subtitle:
        ax.text(
            x + w / 2,
            y + h / 2 - 2.2,
            subtitle,
            ha="center",
            va="center",
            fontsize=9,
            color=ink_muted,
            linespacing=1.3,
        )


def arrow(ax, x0, x1, y, color, outline=False):
    if outline:
        ax.plot(
            [x0, x1],
            [y, y],
            color=box_edge,
            linewidth=5.2,
            solid_capstyle="butt",
            zorder=2,
        )
    ax.plot(
        [x0, x1],
        [y, y],
        color=color,
        linewidth=3.4,
        solid_capstyle="butt",
        zorder=3,
    )
    direction = 1 if x1 > x0 else -1
    tip = [
        (x1, y),
        (x1 - direction * 1.8, y + 1.1),
        (x1 - direction * 1.8, y - 1.1),
    ]
    ax.add_patch(
        Polygon(
            tip,
            closed=True,
            facecolor=color,
            edgecolor=box_edge if outline else color,
            zorder=4,
        )
    )


def wiring_b():
    fig, ax = plt.subplots(figsize=(12, 6.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")
    box(ax, 1, 8, 16, 42, "Keypad", "MS-SN-KB12D\nJP4", fill="#e7efe9")
    box(ax, 83, 8, 16, 42, "Mainboard", "JP4 cable\nend", fill="#e7efe9")
    box(ax, 28, 28, 14, 20, "KW-525 #1", "keypad side\nDB9")
    box(ax, 58, 28, 14, 20, "KW-525 #2", "mainboard side\nDB9")
    box(ax, 42, 51, 16, 8, "PC", "forwards or overrides", fill="#eef4fc")
    ax.plot([35, 35, 42], [48, 55, 55], color=box_edge, linewidth=1.5)
    ax.plot([65, 65, 58], [48, 55, 55], color=box_edge, linewidth=1.5)
    ax.text(33.5, 52, "USB", fontsize=8.5, color=ink_muted, ha="right")
    ax.text(66.5, 52, "USB", fontsize=8.5, color=ink_muted)

    arrow(ax, 17, 28, 42, wire["blue"])
    ax.text(22.5, 43.6, "Blue", ha="center", fontsize=9.5, color=ink)
    ax.text(
        22.5, 40.4, "to DB9 2", ha="center", va="top", fontsize=8.5, color=ink
    )
    arrow(ax, 28, 17, 34, wire["white"], outline=True)
    ax.text(22.5, 35.6, "White", ha="center", fontsize=9.5, color=ink)
    ax.text(
        22.5, 32.4, "from DB9 3", ha="center", va="top", fontsize=8.5, color=ink
    )

    arrow(ax, 72, 83, 42, wire["blue"])
    ax.text(77.5, 43.6, "Blue", ha="center", fontsize=9.5, color=ink)
    ax.text(
        77.5,
        40.4,
        "from DB9 3",
        fontsize=8.5,
        color=ink,
        ha="center",
        va="top",
    )
    arrow(ax, 83, 72, 34, wire["white"], outline=True)
    ax.text(77.5, 35.6, "White", ha="center", fontsize=9.5, color=ink)
    ax.text(
        77.5,
        32.4,
        "to DB9 2",
        fontsize=8.5,
        color=ink,
        ha="center",
        va="top",
    )

    ax.plot([17, 83], [19, 19], color=wire["red"], linewidth=3.4, zorder=3)
    ax.text(
        50,
        20.3,
        "Red +5 V, straight through",
        ha="center",
        fontsize=9.5,
        color=ink,
    )
    ax.plot([17, 83], [12, 12], color=wire["black"], linewidth=3.4, zorder=3)
    ax.text(
        50,
        9.2,
        "Black GND, straight through, shared with both DB9 pin 5",
        ha="center",
        fontsize=9.5,
        color=ink,
    )
    for x in (35, 65):
        ax.plot([x, x], [12, 28], color=wire["black"], linewidth=2.2, zorder=2)
        ax.add_patch(plt.Circle((x, 12), 0.8, color=wire["black"], zorder=4))
        ax.text(
            x + 0.8,
            25.2,
            "5 GND",
            fontsize=8.5,
            color=ink,
            family="DejaVu Sans Mono",
        )
    ax.text(
        50,
        44,
        "Blue and White are cut\nbetween the boards",
        ha="center",
        va="center",
        fontsize=9.5,
        color="#a33a1c",
        bbox={
            "boxstyle": "round,pad=0.4",
            "facecolor": "#fdece6",
            "edgecolor": "#e9a58f",
        },
    )
    return fig


def db9_faces():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    roles = {2: ("RXD", series_blue), 3: ("TXD", "#c23b2e"), 5: ("GND", ink)}
    layouts = [
        (
            "KW-525 cable end (male, pin side)",
            [1, 2, 3, 4, 5],
            [6, 7, 8, 9],
            True,
        ),
        (
            "Screw-terminal adapter (female, socket side)",
            [5, 4, 3, 2, 1],
            [9, 8, 7, 6],
            False,
        ),
    ]
    for ax, (title, top_row, bottom_row, male) in zip(axes, layouts):
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 60)
        ax.axis("off")
        ax.set_title(title, fontsize=11.5, color=ink)
        ax.add_patch(
            Polygon(
                [(5, 50), (95, 50), (84, 12), (16, 12)],
                closed=True,
                facecolor=box_fill,
                edgecolor=box_edge,
                linewidth=2,
            )
        )
        for pins, y, x0 in ((top_row, 39, 18), (bottom_row, 23, 26)):
            for i, pin in enumerate(pins):
                x = x0 + i * 16
                label, color = roles.get(pin, (None, None))
                if male:
                    face = color or "#c9c8c2"
                    ax.add_patch(
                        plt.Circle(
                            (x, y), 5.2, facecolor=face, edgecolor="none"
                        )
                    )
                    ax.text(
                        x,
                        y,
                        str(pin),
                        ha="center",
                        va="center",
                        fontsize=12,
                        fontweight="bold",
                        color=surface if color else ink,
                    )
                else:
                    edge = color or "#c9c8c2"
                    ax.add_patch(
                        plt.Circle(
                            (x, y),
                            4.8,
                            facecolor=surface,
                            edgecolor=edge,
                            linewidth=3,
                        )
                    )
                    ax.text(
                        x,
                        y,
                        str(pin),
                        ha="center",
                        va="center",
                        fontsize=12,
                        fontweight="bold",
                        color=color or ink_muted,
                    )
                if label:
                    ax.text(
                        x,
                        y + 7.2,
                        label,
                        ha="center",
                        fontsize=9,
                        color=ink,
                        family="DejaVu Sans Mono",
                    )
        ax.text(
            50,
            4,
            "pin 1 top-left" if male else "mirrored: pin 1 top-right",
            ha="center",
            fontsize=9.5,
            color=ink_muted,
        )
    return fig


def text_boxes(fig, renderer):
    boxes = []
    for text in fig.findobj(matplotlib.text.Text):
        if not text.get_visible() or not text.get_text().strip():
            continue
        boxes.append((text, text.get_window_extent(renderer).shrunk(0.98, 0.9)))
    return boxes


def axis_furniture(fig):
    skip = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            skip.update(axis.get_gridlines())
            skip.update(axis.get_ticklines())
            skip.update(axis.get_minorticklines())
    return skip


def line_points(line):
    xy = line.get_xydata()
    if len(xy) == 0:
        return []
    if line.get_drawstyle() == "steps-post":
        stepped = []
        for (x0, y0), (x1, _) in zip(xy, xy[1:]):
            stepped += [(x0, y0), (x1, y0)]
        stepped.append(tuple(xy[-1]))
        xy = stepped
    display = line.get_transform().transform(xy)
    points = []
    for (x0, y0), (x1, y1) in zip(display, display[1:]):
        steps = max(2, int(max(abs(x1 - x0), abs(y1 - y0))))
        for k in range(steps + 1):
            points.append(
                (x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps)
            )
    return points


def check_layout(fig):
    """Return human-readable overlaps between text and other artists."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = text_boxes(fig, renderer)
    problems = []
    for i, (text_a, box_a) in enumerate(boxes):
        for text_b, box_b in boxes[i + 1 :]:
            if box_a.overlaps(box_b):
                problems.append(
                    f"text/text: {text_a.get_text()!r} x {text_b.get_text()!r}"
                )
    skip = axis_furniture(fig)
    for line in fig.findobj(matplotlib.lines.Line2D):
        if line in skip or not line.get_visible():
            continue
        points = line_points(line)
        for text, box in boxes:
            if any(box.contains(x, y) for x, y in points):
                problems.append(
                    f"line/text: {line.get_label()!r} x {text.get_text()!r}"
                )
    own_patches = {t.get_bbox_patch() for t, _ in boxes if t.get_bbox_patch()}
    for patch in fig.findobj(matplotlib.patches.Patch):
        if (
            patch in own_patches
            or patch is fig.patch
            or any(patch is ax.patch for ax in fig.axes)
            or patch.get_gid() == "background"
            or not patch.get_visible()
            or isinstance(patch, matplotlib.patches.FancyArrowPatch)
        ):
            continue
        extent = patch.get_window_extent(renderer)
        if extent.width < 1 or extent.height < 1:
            continue
        for text, box in boxes:
            inside = (
                extent.x0 <= box.x0
                and box.x1 <= extent.x1
                and extent.y0 <= box.y0
                and box.y1 <= extent.y1
            )
            if box.overlaps(extent) and not inside:
                problems.append(
                    f"shape/text: {type(patch).__name__} x {text.get_text()!r}"
                )
    return problems


if __name__ == "__main__":
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    for draw in (frame_anatomy, run_profile, wiring_b, db9_faces):
        fig = draw()
        problems = check_layout(fig)
        print(f"{draw.__name__}: {len(problems)} overlap(s)")
        for problem in problems:
            print("   ", problem)
        failed = failed or bool(problems)
        fig.savefig(
            out_dir / f"{draw.__name__}.png", dpi=150, bbox_inches="tight"
        )
        plt.close(fig)
    raise SystemExit(1 if failed else 0)
