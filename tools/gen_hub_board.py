"""Microduck HUB RevA 生成器 + Gerber/Excellon 写入工具。
纯无源 5 路 3 线总线板：DATA / VBAT / GND，附带电池输入、保险丝、开关、1000uF。
输出：Gerber(RS-274X) + Excellon + 1:1 SVG + PNG 预览 + pads.csv。

注意：本仓库当前出板版本是 RevC，由 gen_hub_v2.py 负责；那里只借用本文件的
text_shape / write_gerber / write_drill。单独运行本脚本会把 48 x 48 mm 的 RevA
（已被淘汰的初版）写到 build/revA/，不会覆盖 hardware/ 里的 RevC 产物。
"""
import csv
import json
import pathlib
import zipfile
import shapely.geometry as sg
from shapely.ops import unary_union
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen


ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "revA"
W, H = 48.0, 48.0
PADS, TRACES, TEXT, NPTH = [], [], [], []


def pad(net, x, y, drill=1.0, dia=1.9, name=""):
    PADS.append(dict(net=net, x=float(x), y=float(y), drill=float(drill), dia=float(dia), name=name))


def tr(net, pts, w=2.0, layer="both"):
    TRACES.append(dict(net=net, pts=[(float(a), float(b)) for a, b in pts], w=float(w), layer=layer))


def txt(s, x, y, h=1.2, anchor="left"):
    TEXT.append(dict(s=s, x=float(x), y=float(y), h=float(h), anchor=anchor))


FONT_PATH = "/System/Library/Fonts/Supplemental/Arial.ttf"
FT = TTFont(FONT_PATH)
GS = FT.getGlyphSet()
CMAP = FT.getBestCmap()
UPEM = FT["head"].unitsPerEm
HMTX = FT["hmtx"]
CAP = FT["OS/2"].sCapHeight or int(UPEM * 0.72)


class FlatPen(BasePen):
    def __init__(self, gs, steps=10):
        super().__init__(gs)
        self.steps = steps
        self.contours = []
        self.cur = None

    def _moveTo(self, p):
        self.cur = [p]
        self.contours.append(self.cur)

    def _lineTo(self, p):
        self.cur.append(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            m = 1 - t
            self.cur.append((
                m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
                m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1]))

    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for i in range(1, self.steps + 1):
            t = i / self.steps
            m = 1 - t
            self.cur.append((
                m * m * p0[0] + 2 * m * t * p1[0] + t * t * p2[0],
                m * m * p0[1] + 2 * m * t * p1[1] + t * t * p2[1]))

    def _closePath(self):
        pass

    def _endPath(self):
        pass


def text_shape(s, h):
    scale = h / CAP
    ox = 0.0
    rings = []
    for ch in s:
        g = CMAP.get(ord(ch))
        if g is None:
            ox += 0.35 * UPEM * scale
            continue
        pen = FlatPen(GS)
        GS[g].draw(pen)
        for c in pen.contours:
            pts = [((ox + px) * scale, py * scale) for px, py in c]
            if len(pts) < 4:
                continue
            p = sg.Polygon(pts)
            if not p.is_valid:
                p = p.buffer(0)
            for q in getattr(p, "geoms", [p]):
                if q.area > 1e-6:
                    rings.append(q)
        ox += HMTX[g][0]
    if not rings:
        return None, 0.0
    rings.sort(key=lambda p: -p.area)
    depth = [0] * len(rings)
    for i in range(len(rings)):
        rp = rings[i].representative_point()
        for j in range(i):
            if rings[j].contains(rp):
                depth[i] += 1
    solids = [rings[i] for i in range(len(rings)) if depth[i] % 2 == 0]
    holes = [rings[i] for i in range(len(rings)) if depth[i] % 2 == 1]
    shape = unary_union(solids)
    if holes:
        shape = shape.difference(unary_union(holes))
    return shape, ox * scale


def build_geometry():
    px = [7.0, 15.5, 24.0, 32.5, 41.0]
    names = ["HAT", "IMU", "LLEG", "RLEG", "AUX"]
    y1, y2, y3 = 41.5, 38.96, 36.42
    for i, x in enumerate(px):
        pad("DATA", x, y1, name="J%d.S" % (i + 1))
        pad("VBAT", x, y2, name="J%d.+" % (i + 1))
        pad("GND", x, y3, name="J%d.G" % (i + 1))
        txt(names[i], x, 43.6, 1.3, "center")
        txt("S", x - 2.05, y1 - 0.45, 0.9, "center")
        txt("+", x - 2.05, y2 - 0.45, 0.9, "center")
        txt("G", x - 2.05, y3 - 0.45, 0.9, "center")
    tr("DATA", [(px[0], y1), (px[-1], y1)], 0.6, "top")
    tr("VBAT", [(px[0], y2), (44.5, y2)], 2.0)
    tr("GND", [(4.0, y3), (px[-1], y3)], 2.0)
    tr("VBAT", [(44.5, y2), (44.5, 26.0), (31.54, 26.0)], 2.0)
    tr("VBAT", [(31.54, 26.0), (31.54, 9.0)], 2.0)
    tr("GND", [(4.0, y3), (4.0, 2.0), (39.5, 2.0)], 2.0)
    pad("GND", 9.0, 9.0, 1.3, 2.6, "J6.1")
    pad("BATP", 14.08, 9.0, 1.3, 2.6, "J6.2")
    tr("GND", [(9.0, 9.0), (9.0, 2.0)], 2.0)
    tr("BATP", [(14.08, 9.0), (20.0, 9.0)], 2.0)
    pad("BATP", 20.0, 9.0, 1.1, 2.4, "F1.1")
    pad("BATP2", 25.08, 9.0, 1.1, 2.4, "F1.2")
    tr("BATP2", [(25.08, 9.0), (29.0, 9.0)], 2.0)
    pad("BATP2", 29.0, 9.0, name="J7.IN")
    pad("VBAT", 31.54, 9.0, name="J7.OUT")
    pad("NC", 34.08, 9.0, name="J7.NC")
    pad("VBAT", 39.5, 26.0, 1.0, 2.2, "C1.+")
    pad("GND", 39.5, 21.0, 1.0, 2.2, "C1.-")
    tr("GND", [(39.5, 21.0), (39.5, 2.0)], 2.0)
    NPTH.append((8.0, 32.0, 2.7))
    NPTH.append((40.0, 32.0, 2.7))
    txt("BAT", 11.5, 14.0, 1.1, "center")
    txt("+", 14.08, 11.3, 1.5, "center")
    txt("-", 9.0, 11.3, 1.5, "center")
    txt("F1 5A", 22.5, 12.5, 1.1, "center")
    txt("SW", 31.54, 6.2, 1.1, "center")
    txt("C1 1000U/16V", 37.0, 16.5, 1.1, "right")
    txt("MICRODUCK HUB REVA", 13.0, 33.5, 1.15, "left")
    txt("S=BUS  +=BAT  G=GND", 13.0, 31.0, 0.95, "left")


def silk_shapes():
    out = []
    for item in TEXT:
        shape, adv = text_shape(item["s"], item["h"])
        if shape is None:
            continue
        x0 = shape.bounds[0]
        x1 = shape.bounds[2]
        if item["anchor"] == "center":
            dx = item["x"] - (x0 + x1) / 2.0
        elif item["anchor"] == "right":
            dx = item["x"] - x1
        else:
            dx = item["x"] - x0
        from shapely.affinity import translate
        out.append(translate(shape, xoff=dx, yoff=item["y"]))
    ring = sg.Point(39.5, 23.5).buffer(5.2, 64).difference(sg.Point(39.5, 23.5).buffer(5.0, 64))
    out.append(ring)
    return out


def copper_shapes(layer):
    res = []
    for p in PADS:
        res.append((p["net"], sg.Point(p["x"], p["y"]).buffer(p["dia"] / 2.0, 48)))
    for t in TRACES:
        if t["layer"] == "top" and layer != "top":
            continue
        res.append((t["net"], sg.LineString(t["pts"]).buffer(t["w"] / 2.0, cap_style=1, join_style=1, resolution=16)))
    return res


def check():
    msgs = []
    board = sg.box(0.3, 0.3, W - 0.3, H - 0.3)
    for layer in ("top", "bottom"):
        shapes = copper_shapes(layer)
        for net in {n for n, _ in shapes}:
            merged = unary_union([s for n, s in shapes if n == net])
            if not board.contains(merged):
                msgs.append("edge: %s %s 超出板边内缩 0.3mm" % (layer, net))
        nets = sorted({n for n, _ in shapes})
        for i in range(len(nets)):
            for j in range(i + 1, len(nets)):
                a = unary_union([s for n, s in shapes if n == nets[i]])
                b = unary_union([s for n, s in shapes if n == nets[j]])
                d = a.distance(b)
                if d < 0.2:
                    msgs.append("clearance %s: %s <-> %s = %.3f mm" % (layer, nets[i], nets[j], d))
    return msgs


def cint(v):
    return str(int(round(v * 1000000)))


def write_gerber(path, flashes, strokes, regions, title):
    ap = {}
    order = []

    def code(d):
        k = round(d, 3)
        if k not in ap:
            ap[k] = 10 + len(ap)
            order.append(k)
        return ap[k]

    body = []
    for x, y, d in flashes:
        body.append("D%d*" % code(d))
        body.append("X%sY%sD03*" % (cint(x), cint(y)))
    for pts, w in strokes:
        body.append("D%d*" % code(w))
        body.append("X%sY%sD02*" % (cint(pts[0][0]), cint(pts[0][1])))
        for x, y in pts[1:]:
            body.append("X%sY%sD01*" % (cint(x), cint(y)))
    cur_pol = "D"
    for poly, pol in regions:
        if pol != cur_pol:
            body.append("%%LP%s*%%" % ("D" if pol == "D" else "C"))
            cur_pol = pol
        body.append("G36*")
        coords = list(poly.exterior.coords)
        body.append("X%sY%sD02*" % (cint(coords[0][0]), cint(coords[0][1])))
        body.append("G01*")
        for x, y in coords[1:]:
            body.append("X%sY%sD01*" % (cint(x), cint(y)))
        body.append("G37*")
    if cur_pol != "D":
        body.append("%LPD*%")
    head = ["G04 " + title + "*", "%FSLAX46Y46*%", "%MOMM*%", "%LPD*%"]
    for k in order:
        head.append("%%ADD%dC,%.3f*%%" % (ap[k], k))
    head.append("G01*")
    pathlib.Path(path).write_text("\n".join(head + body + ["M02*"]) + "\n", encoding="utf-8")


def write_drill(path, holes):
    byd = {}
    for x, y, d in holes:
        byd.setdefault(round(d, 2), []).append((x, y))
    lines = ["M48", ";DRILL file {Microduck HUB RevA}",
             ";FORMAT={-:-/ absolute / metric / decimal}", "FMAT,2", "METRIC"]
    keys = sorted(byd)
    for i, d in enumerate(keys):
        lines.append("T%dC%.3f" % (i + 1, d))
    lines.append("%")
    lines.append("G90")
    lines.append("G05")
    for i, d in enumerate(keys):
        lines.append("T%d" % (i + 1))
        for x, y in byd[d]:
            lines.append("X%.3fY%.3f" % (x, y))
    lines.append("M30")
    pathlib.Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit():
    OUT.mkdir(parents=True, exist_ok=True)
    top = copper_shapes("top")
    bot = copper_shapes("bottom")
    holes = [(p["x"], p["y"], p["drill"]) for p in PADS] + [(x, y, d) for x, y, d in NPTH]
    flashes = [(p["x"], p["y"], p["dia"]) for p in PADS]
    flashes_mask = [(p["x"], p["y"], p["dia"] + 0.1) for p in PADS]
    strokes = [(t["pts"], t["w"]) for t in TRACES if t["layer"] == "top"]
    strokes_bot = [(t["pts"], t["w"]) for t in TRACES if t["layer"] == "both"]
    silk = silk_shapes()
    regions = []
    for s in silk:
        for poly in getattr(s, "geoms", [s]):
            regions.append((sg.Polygon(poly.exterior), "D"))
            for r in poly.interiors:
                regions.append((sg.Polygon(r), "C"))
    write_gerber(OUT / "Microduck-HUB-RevA-F_Cu.gtl", flashes, strokes, [], "F.Cu")
    write_gerber(OUT / "Microduck-HUB-RevA-B_Cu.gbl", flashes, strokes_bot, [], "B.Cu")
    write_gerber(OUT / "Microduck-HUB-RevA-F_Mask.gts", flashes_mask, [], [], "F.Mask")
    write_gerber(OUT / "Microduck-HUB-RevA-B_Mask.gbs", flashes_mask, [], [], "B.Mask")
    write_gerber(OUT / "Microduck-HUB-RevA-F_Silkscreen.gto", [], [], regions, "F.SilkS")
    write_gerber(OUT / "Microduck-HUB-RevA-B_Silkscreen.gbo", [], [], [], "B.SilkS")
    write_gerber(OUT / "Microduck-HUB-RevA-Edge_Cuts.gko", [], [([(0, 0), (W, 0), (W, H), (0, H), (0, 0)], 0.1)], [], "Edge.Cuts")
    write_drill(OUT / "Microduck-HUB-RevA.drl", holes)
    with (OUT / "pads.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pad", "net", "x_mm", "y_mm", "drill_mm", "pad_mm"])
        for p in PADS:
            w.writerow([p["name"], p["net"], p["x"], p["y"], p["drill"], p["dia"]])
    meta = dict(width=W, height=H, pads=PADS, traces=TRACES)
    (OUT / "board.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    build_geometry()
    problems = check()
    emit()
    print("pads=%d traces=%d text=%d" % (len(PADS), len(TRACES), len(TEXT)))
    if problems:
        print("CHECK:")
        for m in problems:
            print(" -", m)
    else:
        print("CHECK: ok")
