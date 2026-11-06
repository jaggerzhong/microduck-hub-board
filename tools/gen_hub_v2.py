"""Microduck HUB RevB generator -- official 23 x 34 mm outline.

Board: 2 layer, 1.0 mm, pure passive bus hub.
  B.Cu : VBAT only (wide trunk)
  F.Cu : GND ring + DATA star
Ports (official pad map from docs/assets/assembly-hub-layout.json):
  CN2 bottom-left  = HAT   pin1 DATA / pin2 VBAT / pin3 GND
  CN3 bottom-right = IMU   pin1 DATA / pin2 VBAT / pin3 GND
  CN4 right-lower  = RLEG  pin1 DATA / pin2 VBAT / pin3 GND
  CN5 left-lower   = LLEG  pin1 DATA / pin2 VBAT / pin3 GND
  CN1 top          = BAT   pin1 GND  / pin2 VBAT
  C1  bottom       = 1000 uF, pin1(+) VBAT at x=-1.75, pin2 GND at x=+1.75
Output: Gerber RS-274X + Excellon + preview.png + pads.csv + board.json + zip.

RevC (2026-11-06): mounting holes changed from 4 x D1.2 @ 19 x 30 to
4 x D2.2 (M2 clearance) @ 30 x 16, matching the HD1910 housing hole pattern
so the same M2 hardware as the rest of the robot works. GND ring pulled in
from x=+-7.4 to x=+-5.9 to keep >=0.3 mm to the bigger holes.
"""
import csv
import json
import pathlib
import sys
import zipfile

import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.affinity import translate, scale

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_hub_board import text_shape, write_gerber, write_drill

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "hardware" / "gerber"
DATA = ROOT / "hardware"
IMG = ROOT / "hardware" / "img"
NAME = "Microduck-HUB-RevC"
THICK = 1.0

OUTLINE = [
    (-10.5, 17.0), (10.5, 17.0), (10.69509, 16.98078), (10.88268, 16.92388),
    (11.05557, 16.83147), (11.20711, 16.70711), (11.33147, 16.55557),
    (11.42388, 16.38268), (11.48078, 16.19509), (11.5, 16.0), (11.5, 3.5),
    (8.5, 3.5), (8.5, -5.5), (11.5, -5.5), (11.5, -16.0),
    (11.48078, -16.19509), (11.42388, -16.38268), (11.33147, -16.55557),
    (11.20711, -16.70711), (11.05557, -16.83147), (10.88268, -16.92388),
    (10.69509, -16.98078), (10.5, -17.0), (-10.5, -17.0),
    (-10.69509, -16.98078), (-10.88268, -16.92388), (-11.05557, -16.83147),
    (-11.20711, -16.70711), (-11.33147, -16.55557), (-11.42388, -16.38268),
    (-11.48078, -16.19509), (-11.5, -16.0), (-11.5, -5.5), (-8.5, -5.5),
    (-8.5, 3.5), (-11.5, 3.5), (-11.5, 16.0), (-11.48078, 16.19509),
    (-11.42388, 16.38268), (-11.33147, 16.55557), (-11.20711, 16.70711),
    (-11.05557, 16.83147), (-10.88268, 16.92388), (-10.69509, 16.98078),
    (-10.5, 17.0),
]

# M2 clearance: pitch 30 x 16 = HD1910 housing hole pattern, hole D2.2.
# RevC: the servo's four mounting holes are D1.6 at 30 x 16 (spec 9, outline
# drawing), so the PCB holes follow that pattern instead of the old 19 x 30.
NPTH = [(-8.0, 15.0, 2.2), (8.0, 15.0, 2.2), (-8.0, -15.0, 2.2), (8.0, -15.0, 2.2)]

PADS, TRACES, TEXT = [], [], []


def pad(net, x, y, name, drill=1.0, dia=1.5):
    PADS.append(dict(net=net, x=float(x), y=float(y), drill=float(drill),
                     dia=float(dia), name=name))


def tr(net, pts, w, layer):
    TRACES.append(dict(net=net, pts=[(float(a), float(b)) for a, b in pts],
                       w=float(w), layer=layer))


def txt(s, x, y, h=0.85, both=False):
    TEXT.append(dict(s=s, x=float(x), y=float(y), h=float(h), layer="F"))
    if both:
        TEXT.append(dict(s=s, x=float(x), y=float(y), h=float(h), layer="B"))


def build_geometry():
    # ---- pads, exact official positions -------------------------------
    pad("GND", -4.055, 7.0, "CN2.GND")
    pad("VBAT", -4.055, 9.0, "CN2.VBAT")
    pad("DATA", -4.055, 11.0, "CN2.DATA")
    pad("GND", 4.055, 11.0, "CN3.GND")
    pad("VBAT", 4.055, 9.0, "CN3.VBAT")
    pad("DATA", 4.055, 7.0, "CN3.DATA")
    pad("GND", 4.055, -7.0, "CN4.GND")
    pad("VBAT", 4.055, -9.0, "CN4.VBAT")
    pad("DATA", 4.055, -11.0, "CN4.DATA")
    pad("GND", -4.055, -11.0, "CN5.GND")
    pad("VBAT", -4.055, -9.0, "CN5.VBAT")
    pad("DATA", -4.055, -7.0, "CN5.DATA")
    pad("VBAT", -1.75006, 0.0, "C1.+", 1.0, 1.6)
    pad("GND", 1.75006, 0.0, "C1.-", 1.0, 1.6)
    pad("GND", -1.25006, -13.4, "CN1.GND")
    pad("VBAT", 1.25006, -13.4, "CN1.VBAT")

    # ---- B.Cu : VBAT ---------------------------------------------------
    B = "B"
    tr("VBAT", [(-4.055, 9.0), (4.055, 9.0)], 1.5, B)
    tr("VBAT", [(-4.055, 9.0), (-6.3, 9.0)], 1.5, B)
    tr("VBAT", [(-6.3, 9.0), (-6.3, -9.0)], 1.8, B)
    tr("VBAT", [(-6.3, -9.0), (-4.055, -9.0)], 1.5, B)
    tr("VBAT", [(4.055, 9.0), (6.3, 9.0)], 1.5, B)
    tr("VBAT", [(6.3, 9.0), (6.3, -13.4)], 1.8, B)
    tr("VBAT", [(6.3, -13.4), (1.25006, -13.4)], 1.5, B)
    tr("VBAT", [(4.055, -9.0), (6.3, -9.0)], 1.5, B)
    tr("VBAT", [(-1.75006, 0.0), (-6.3, 0.0)], 1.2, B)

    # ---- F.Cu : GND + DATA ---------------------------------------------
    F = "F"
    # GND ring pulled in to x=+-5.9 so the M2 holes at x=+-8 keep >=0.3 mm
    tr("GND", [(-4.055, 7.0), (-5.9, 7.0)], 1.2, F)
    tr("GND", [(-5.9, 7.0), (-5.9, -15.5)], 1.2, F)
    tr("GND", [(-5.9, -11.0), (-4.055, -11.0)], 1.2, F)
    tr("GND", [(4.055, 11.0), (5.9, 11.0)], 1.2, F)
    tr("GND", [(5.9, 11.0), (5.9, -15.5)], 1.2, F)
    tr("GND", [(5.9, -7.0), (4.055, -7.0)], 1.2, F)
    tr("GND", [(-5.9, -15.5), (5.9, -15.5)], 1.2, F)
    tr("GND", [(1.75006, 0.0), (5.9, 0.0)], 1.2, F)
    tr("GND", [(-1.25006, -13.4), (-1.25006, -15.5)], 1.0, F)
    tr("DATA", [(-4.055, 11.0), (0.0, 11.0)], 0.3, F)
    tr("DATA", [(4.055, 7.0), (0.0, 7.0)], 0.3, F)
    tr("DATA", [(0.0, 11.0), (0.0, -11.0)], 0.3, F)
    tr("DATA", [(-4.055, -7.0), (0.0, -7.0)], 0.3, F)
    tr("DATA", [(4.055, -11.0), (0.0, -11.0)], 0.3, F)

    # ---- silkscreen -----------------------------------------------------
    txt("HUB-B", 0.0, 14.3, 0.95)
    txt("HAT", -8.1, 8.6, 0.85, True)
    txt("IMU", 7.5, 8.6, 0.85, True)
    txt("LLEG", -8.0, -10.7, 0.80, True)
    txt("RLEG", 7.6, -10.7, 0.80, True)
    txt("BAT", -4.35, -13.4, 0.85)
    txt("+", 2.5, -13.4, 0.95)
    txt("1000U", 0.0, 5.4, 0.80)
    txt("+", -1.75, 2.9, 0.90)
    for x, y in ((-5.9, 11.0), (5.9, 7.0), (5.9, -11.0), (-5.9, -7.0),
                 (-2.55, -13.4)):
        txt("1", x, y, 0.70, True)


def board_poly():
    return sg.Polygon(OUTLINE)


def layer_shapes(layer):
    res = []
    for p in PADS:
        res.append((p["net"], sg.Point(p["x"], p["y"]).buffer(p["dia"] / 2.0, 48)))
    for t in TRACES:
        if t["layer"] != layer:
            continue
        res.append((t["net"], sg.LineString(t["pts"]).buffer(
            t["w"] / 2.0, cap_style=1, join_style=1, resolution=16)))
    return res


def silk_shapes(layer):
    res = []
    for item in TEXT:
        if item["layer"] != layer:
            continue
        shape, _ = text_shape(item["s"], item["h"])
        if shape is None:
            continue
        x0, x1 = shape.bounds[0], shape.bounds[2]
        dx = item["x"] - (x0 + x1) / 2.0
        s = translate(shape, xoff=dx, yoff=item["y"])
        if layer == "B":
            s = scale(s, xfact=-1.0, yfact=1.0, origin=(item["x"], 0.0))
        for g in getattr(s, "geoms", [s]):
            res.append(g)
    return res


def check():
    msgs = []
    poly = board_poly()
    inner = poly.buffer(-0.35)
    for layer in ("F", "B"):
        shapes = layer_shapes(layer)
        nets = sorted({n for n, _ in shapes})
        for net in nets:
            merged = unary_union([s for n, s in shapes if n == net])
            if not inner.contains(merged):
                msgs.append("EDGE %s %s: copper outside 0.35 mm inset" % (layer, net))
        for i in range(len(nets)):
            for j in range(i + 1, len(nets)):
                a = unary_union([s for n, s in shapes if n == nets[i]])
                b = unary_union([s for n, s in shapes if n == nets[j]])
                d = a.distance(b)
                if d < 0.2:
                    msgs.append("CLEAR %s %s<->%s = %.3f" % (layer, nets[i], nets[j], d))
    for p in PADS:
        if p["drill"] >= p["dia"]:
            msgs.append("PAD %s drill>=pad" % p["name"])
    keep = [sg.Point(p["x"], p["y"]).buffer(p["dia"] / 2.0 + 0.1, 32) for p in PADS]
    for layer in ("F", "B"):
        for s in silk_shapes(layer):
            if not inner.contains(s):
                msgs.append("SILK %s outside inset: bounds=%s" % (layer, [round(v, 2) for v in s.bounds]))
            for k in keep:
                if s.distance(k) < 0.05:
                    msgs.append("SILK %s touches pad keepout at %s" % (layer, [round(v, 1) for v in s.bounds]))
                    break
    for x, y, d in NPTH:
        if not poly.contains(sg.Point(x, y)):
            msgs.append("HOLE %.2f,%.2f outside board" % (x, y))
        hole = sg.Point(x, y).buffer(d / 2.0, 48)
        if poly.exterior.distance(hole) < 0.5:
            msgs.append("HOLE %.2f,%.2f edge distance %.2f < 0.5"
                        % (x, y, poly.exterior.distance(hole)))
        for layer in ("F", "B"):
            for net, s in layer_shapes(layer):
                gap = hole.distance(s)
                if gap < 0.3:
                    msgs.append("HOLE %.1f,%.1f %s %s clearance %.2f < 0.3"
                                % (x, y, layer, net, gap))
    return msgs


def preview():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MPoly

    fig, ax = plt.subplots(figsize=(4.2, 6.0), dpi=170)
    ax.add_patch(MPoly(OUTLINE, closed=True, facecolor="#0f2f1f", edgecolor="none"))
    for net, s in layer_shapes("B"):
        for g in getattr(s, "geoms", [s]):
            ax.add_patch(MPoly(list(g.exterior.coords), closed=True,
                               facecolor="#c0392b", alpha=0.75, edgecolor="none"))
    for net, s in layer_shapes("F"):
        col = "#2e86c1" if net == "GND" else "#f1c40f"
        for g in getattr(s, "geoms", [s]):
            ax.add_patch(MPoly(list(g.exterior.coords), closed=True,
                               facecolor=col, alpha=0.9, edgecolor="none"))
    for p in PADS:
        ax.add_patch(plt.Circle((p["x"], p["y"]), p["dia"] / 2.0,
                                facecolor="#d5d8dc", edgecolor="#7f8c8d", lw=0.4))
        ax.add_patch(plt.Circle((p["x"], p["y"]), p["drill"] / 2.0,
                                facecolor="#0f2f1f", edgecolor="none"))
    for x, y, d in NPTH:
        ax.add_patch(plt.Circle((x, y), d / 2.0, facecolor="#0f2f1f",
                                edgecolor="#ffffff", lw=0.4))
    for s in silk_shapes("F"):
        ax.add_patch(MPoly(list(s.exterior.coords), closed=True,
                           facecolor="#ffffff", edgecolor="none"))
    ax.plot([p[0] for p in OUTLINE], [p[1] for p in OUTLINE], color="#f7dc6f", lw=0.8)
    ax.set_xlim(-13.2, 13.2)
    ax.set_ylim(-19.0, 19.0)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Microduck HUB RevC 23 x 34 x 1.0", fontsize=8)
    fig.tight_layout()
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / "preview.png")
    plt.close(fig)


def emit():
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    flashes = [(p["x"], p["y"], p["dia"]) for p in PADS]
    mask = [(p["x"], p["y"], p["dia"] + 0.1) for p in PADS]
    f_str = [(t["pts"], t["w"]) for t in TRACES if t["layer"] == "F"]
    b_str = [(t["pts"], t["w"]) for t in TRACES if t["layer"] == "B"]
    holes = [(p["x"], p["y"], p["drill"]) for p in PADS] + list(NPTH)

    def regions(shape_list):
        out = []
        for s in shape_list:
            out.append((sg.Polygon(s.exterior), "D"))
            for r in s.interiors:
                out.append((sg.Polygon(r), "C"))
        return out

    write_gerber(OUT / (NAME + "-F_Cu.gtl"), flashes, f_str, [], "F.Cu")
    write_gerber(OUT / (NAME + "-B_Cu.gbl"), flashes, b_str, [], "B.Cu")
    write_gerber(OUT / (NAME + "-F_Mask.gts"), mask, [], [], "F.Mask")
    write_gerber(OUT / (NAME + "-B_Mask.gbs"), mask, [], [], "B.Mask")
    write_gerber(OUT / (NAME + "-F_Silkscreen.gto"), [], [], regions(silk_shapes("F")), "F.SilkS")
    write_gerber(OUT / (NAME + "-B_Silkscreen.gbo"), [], [], regions(silk_shapes("B")), "B.SilkS")
    write_gerber(OUT / (NAME + "-Edge_Cuts.gko"), [], [(OUTLINE, 0.1)], [], "Edge.Cuts")
    write_drill(OUT / (NAME + ".drl"), holes)

    with (DATA / "pads.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pad", "net", "x_mm", "y_mm", "drill_mm", "pad_mm"])
        for p in PADS:
            w.writerow([p["name"], p["net"], p["x"], p["y"], p["drill"], p["dia"]])
    meta = dict(name=NAME, width=23.0, height=34.0, thickness=THICK,
                outline=OUTLINE, holes=NPTH, pads=PADS, traces=TRACES)
    (DATA / "board.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    preview()

    zpath = OUT / (NAME + "-Gerber.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.name.startswith(NAME) and p.suffix in (".gtl", ".gbl", ".gts", ".gbs",
                                                        ".gto", ".gbo", ".gko", ".drl"):
                z.write(p, p.name)
    return zpath


if __name__ == "__main__":
    build_geometry()
    problems = check()
    zpath = emit()
    print("pads=%d traces=%d text=%d" % (len(PADS), len(TRACES), len(TEXT)))
    print("zip=", zpath)
    if problems:
        print("CHECK:")
        for m in problems:
            print(" -", m)
    else:
        print("CHECK: ok")
