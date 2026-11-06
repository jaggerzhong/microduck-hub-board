#!/usr/bin/env python3
"""Overlay the HD1910 housing footprint on HUB RevC to prove hole alignment.

Servo outline drawing (spec 9, 34 x 20 x 23): four mounting holes D1.6 at
30 x 16 mm. Board holes are D2.2 at the same 30 x 16 pitch, so a centered
servo footprint should put its four holes exactly under the PCB holes.
"""
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as MPoly, Rectangle

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "hardware"
IMG = DATA / "img"
meta = json.loads((DATA / "board.json").read_text(encoding="utf-8"))

fig, ax = plt.subplots(figsize=(5.0, 6.6), dpi=170)
ax.add_patch(MPoly(meta["outline"], closed=True, facecolor="#e8f5e9",
                   edgecolor="#2e7d32", lw=1.2, zorder=1))

# HD1910 housing face: 20 mm across the 23 mm board width, 34 mm along the length.
ax.add_patch(Rectangle((-10, -17), 20, 34, facecolor="none", edgecolor="#d35400",
                       lw=1.0, ls="--", zorder=2, label="HD1910 housing 20 x 34"))
ax.add_patch(Circle((0, 0), 8.0, facecolor="none", edgecolor="#d35400",
                    lw=0.8, ls=":", zorder=2, label="horn boss D16"))

for x, y, d in meta["holes"]:
    ax.add_patch(Circle((x, y), d / 2.0, facecolor="#37474f", edgecolor="none", zorder=3))
    ax.add_patch(Circle((x, y), 0.8, facecolor="#c62828", edgecolor="none",
                        alpha=0.55, zorder=4))

ax.plot([], [], "o", color="#37474f", label="PCB hole D2.2")
ax.plot([], [], "o", color="#c62828", alpha=0.55, label="servo hole D1.6")
ax.set_xlim(-14, 14)
ax.set_ylim(-19, 19)
ax.set_aspect("equal")
ax.grid(True, lw=0.3, color="#cfd8dc")
ax.set_xlabel("x (mm)")
ax.set_ylabel("y (mm)")
ax.set_title("HUB RevC vs HD1910 holes: 30 x 16 pitch", fontsize=9)
ax.legend(fontsize=6.5, loc="upper right")
fig.tight_layout()
IMG.mkdir(parents=True, exist_ok=True)
fig.savefig(IMG / "servo-fit.png")
print("holes:", meta["holes"])
print("servo hole centers must be (+-8, +-15)")
