# Render three z-buffered, shaded views of an ASCII STL into one PNG
# (the DB9 bracket preview in the README). Probe values are inline.
"""Render an ASCII STL from three directions.

Usage:
    render_stl_views.py IN.stl OUT.png [TITLE]

Needs numpy and matplotlib. A small z-buffer rasterizer is used because
matplotlib's 3D axes sort whole faces and let hidden edges show through.
"""

import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

pixels_per_mm = 8.0
margin = 10
base_color = np.array([0.97, 0.5, 0.15])
views = [
    (-60, 30, "front, from above"),
    (-60, 150, "back, from above"),
    (0, 0, "top"),
]


def load_triangles(path):
    vertices = [
        [float(value) for value in line.split()[1:]]
        for line in open(path).read().splitlines()
        if line.strip().startswith("vertex")
    ]
    triangles = np.array(vertices).reshape(-1, 3, 3)
    return triangles - triangles.reshape(-1, 3).mean(0)


def rotation(elevation, azimuth):
    a, e = np.radians(azimuth), np.radians(elevation)
    about_z = np.array(
        [[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]]
    )
    about_x = np.array(
        [[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]]
    )
    return about_x @ about_z


def render(triangles, normals, elevation, azimuth, light):
    turn = rotation(elevation, azimuth)
    points = triangles @ turn.T * pixels_per_mm
    facing = normals @ turn.T
    points[:, :, 1] *= -1
    points[:, :, :2] -= points.reshape(-1, 3).min(0)[:2] - margin
    width = int(points[:, :, 0].max()) + margin + 1
    height = int(points[:, :, 1].max()) + margin + 1
    depth = np.full((height, width), -np.inf)
    image = np.ones((height, width, 3))
    for index, corners in enumerate(points):
        if facing[index, 2] <= 0:
            continue
        (x0, y0, z0), (x1, y1, z1), (x2, y2, z2) = corners
        left = int(max(min(x0, x1, x2), 0))
        right = int(min(max(x0, x1, x2) + 1, width))
        top = int(max(min(y0, y1, y2), 0))
        bottom = int(min(max(y0, y1, y2) + 1, height))
        area = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if left >= right or top >= bottom or abs(area) < 1e-9:
            continue
        x, y = np.meshgrid(
            np.arange(left, right) + 0.5, np.arange(top, bottom) + 0.5
        )
        w0 = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / area
        w1 = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / area
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        z = w0 * z0 + w1 * z1 + w2 * z2
        window = depth[top:bottom, left:right]
        hit = inside & (z > window)
        window[hit] = z[hit]
        shade = 0.3 + 0.7 * max(facing[index] @ light, 0)
        image[top:bottom, left:right][hit] = base_color * shade
    return image


def main():
    triangles = load_triangles(sys.argv[1])
    title = sys.argv[3] if len(sys.argv) > 3 else ""
    edges_a = triangles[:, 1] - triangles[:, 0]
    edges_b = triangles[:, 2] - triangles[:, 0]
    normals = np.cross(edges_a, edges_b)
    normals /= np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12
    light = np.array([-0.35, 0.55, 0.75])
    light /= np.linalg.norm(light)
    figure, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    for axis, (elevation, azimuth, name) in zip(axes, views):
        axis.imshow(render(triangles, normals, elevation, azimuth, light))
        axis.axis("off")
        axis.set_title(name)
    figure.suptitle(title)
    plt.tight_layout()
    plt.savefig(sys.argv[2], dpi=100, facecolor="white")


if __name__ == "__main__":
    main()
