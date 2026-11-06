"""Export HUB RevB geometry as KiCad 5 .kicad_pcb for LCEDA Pro import."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import gen_hub_v2 as g

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "hardware" / ("%s.kicad_pcb" % g.NAME)
MAXY = 17.0

NETS = ["", "VBAT", "GND", "DATA"]
NETID = {n: i for i, n in enumerate(NETS)}


def f(v):
    s = "%.4f" % float(v)
    s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def ky(y):
    return MAXY - float(y)


def pad_line(num, dx, dy, drill, dia, net):
    return ("    (pad %s thru_hole circle (at %s %s) (size %s %s) (drill %s) "
            "(layers *.Cu *.Mask) (net %d \"%s\"))\n"
            % (num, f(dx), f(dy), f(dia), f(dia), f(drill), NETID[net], net))


PARTS = []


def part(ref, value, cx, cy, pads, layer, descr):
    """pads: [(num, world_dx, world_dy, drill, dia, net)] with world dy up-positive."""
    b = []
    b.append("  (module Microduck:%s (layer %s) (tedit 5F3C1A2B) (tstamp 0)\n" % (value, layer))
    b.append("    (at %s %s)\n" % (f(cx), f(ky(cy))))
    b.append("    (descr \"%s\")\n" % descr)
    b.append("    (attr through_hole)\n")
    b.append("    (fp_text reference %s (at 0 -3.6) (layer %s) hide (effects "
             "(font (size 0.7 0.7) (thickness 0.12))))\n"
             % (ref, "B.SilkS" if layer == "B.Cu" else "F.SilkS"))
    b.append("    (fp_text value %s (at 0 3.6) (layer F.Fab) hide (effects "
             "(font (size 0.7 0.7) (thickness 0.12))))\n" % value)
    for num, dx, dy, drill, dia, net in pads:
        b.append(pad_line(num, dx, -dy, drill, dia, net))
    b.append("  )\n\n")
    PARTS.append("".join(b))


def build():
    g.build_geometry()
    by_name = {p["name"]: p for p in g.PADS}

    def pads_of(center, prefix, pinmap, drop=()):
        res = []
        for pin, nm in pinmap.items():
            p = by_name[nm]
            if pin in drop:
                continue
            res.append((pin, p["x"] - center[0], p["y"] - center[1],
                        p["drill"], p["dia"], p["net"]))
        return sorted(res, key=lambda r: r[2])

    part("CN2", "AMP20_3P_HAT", -4.055, 9.0,
         pads_of((-4.055, 9.0), "CN2", {"1": "CN2.DATA", "2": "CN2.VBAT", "3": "CN2.GND"}),
         "B.Cu", "AMP2.0 3P socket, HAT port")
    part("CN3", "AMP20_3P_IMU", 4.055, 9.0,
         pads_of((4.055, 9.0), "CN3", {"1": "CN3.DATA", "2": "CN3.VBAT", "3": "CN3.GND"}),
         "B.Cu", "AMP2.0 3P socket, IMU port")
    part("CN4", "AMP20_3P_RLEG", 4.055, -9.0,
         pads_of((4.055, -9.0), "CN4", {"1": "CN4.DATA", "2": "CN4.VBAT", "3": "CN4.GND"}),
         "B.Cu", "AMP2.0 3P socket, right leg")
    part("CN5", "AMP20_3P_LLEG", -4.055, -9.0,
         pads_of((-4.055, -9.0), "CN5", {"1": "CN5.DATA", "2": "CN5.VBAT", "3": "CN5.GND"}),
         "B.Cu", "AMP2.0 3P socket, left leg")
    part("C1", "CP_1000uF_16V", 0.0, 0.0,
         pads_of((0.0, 0.0), "C1", {"1": "C1.+", "2": "C1.-"}),
         "B.Cu", "1000 uF / 16 V radial, 3.5 mm pitch")
    part("CN1", "BAT_2P", 0.0, -13.4,
         pads_of((0.0, -13.4), "CN1", {"1": "CN1.GND", "2": "CN1.VBAT"}),
         "F.Cu", "battery input 2P")

    holes = []
    for i, (x, y, d) in enumerate(g.NPTH):
        holes.append(
            "  (module Microduck:HUB_Mount_M2 (layer F.Cu) (tedit 5F3C1A2B) (tstamp %d)\n"
            "    (at %s %s)\n    (descr \"M2 clearance mounting hole\")\n    (attr virtual)\n"
            "    (fp_text reference MH%d (at 0 -2.6) (layer F.SilkS) hide (effects "
            "(font (size 0.7 0.7) (thickness 0.12))))\n"
            "    (fp_text value MountingHole (at 0 2.6) (layer F.Fab) hide (effects "
            "(font (size 0.7 0.7) (thickness 0.12))))\n"
            "    (pad 1 np_thru_hole circle (at 0 0) (size %s %s) (drill %s) "
            "(layers *.Cu *.Mask))\n  )\n\n"
            % (i + 1, f(x), f(ky(y)), i + 1, f(d), f(d), f(d)))
    PARTS.append("".join(holes))

    segs = []
    for t in g.TRACES:
        lay = "F.Cu" if t["layer"] == "F" else "B.Cu"
        for i in range(len(t["pts"]) - 1):
            a, b = t["pts"][i], t["pts"][i + 1]
            segs.append("  (segment (start %s %s) (end %s %s) (width %s) "
                        "(layer %s) (net %d))\n"
                        % (f(a[0]), f(ky(a[1])), f(b[0]), f(ky(b[1])),
                           f(t["w"]), lay, NETID[t["net"]]))

    texts = []
    for item in g.TEXT:
        s = item["s"].replace('"', '\\"')
        mirror = " (justify mirror)" if item["layer"] == "B" else ""
        texts.append("  (gr_text \"%s\" (at %s %s) (layer %s) (effects "
                     "(font (size %s %s) (thickness 0.13))%s))\n"
                     % (s, f(item["x"]), f(ky(item["y"])),
                        "B.SilkS" if item["layer"] == "B" else "F.SilkS",
                        f(item["h"] * 1.15), f(item["h"] * 1.15), mirror))

    edges = []
    pts = g.OUTLINE
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        edges.append("  (gr_line (start %s %s) (end %s %s) (layer Edge.Cuts) "
                     "(width 0.1))\n" % (f(a[0]), f(ky(a[1])), f(b[0]), f(ky(b[1]))))

    head = []
    head.append("(kicad_pcb (version 20171130) (host pcbnew \"(5.1.6)-1\")\n\n")
    head.append("  (general\n    (thickness %s)\n  )\n\n" % f(g.THICK))
    head.append("  (page A4)\n")
    head.append("  (title_block\n    (title \"Microduck HUB RevC 23x34\")\n"
                "    (date \"2026-11-06\")\n    (rev \"C\")\n"
                "    (comment 1 \"official outline, 4x AMP2.0 3P + 2P battery + 1000uF\")\n  )\n\n")
    head.append("  (layers\n"
                "    (0 F.Cu signal)\n    (31 B.Cu signal)\n"
                "    (36 B.SilkS user)\n    (37 F.SilkS user)\n"
                "    (38 B.Mask user)\n    (39 F.Mask user)\n"
                "    (44 Edge.Cuts user)\n  )\n\n")
    head.append("  (setup\n    (last_trace_width 0.25)\n    (trace_clearance 0.2)\n"
                "    (zone_clearance 0.508)\n    (trace_min 0.2)\n"
                "    (via_size 0.6)\n    (via_drill 0.3)\n    (via_min_size 0.4)\n"
                "    (via_min_drill 0.3)\n    (uvia_size 0.3)\n    (uvia_drill 0.1)\n"
                "    (uvias_allowed no)\n    (uvia_min_size 0.2)\n    (uvia_min_drill 0.1)\n"
                "    (edge_width 0.1)\n    (segment_width 0.2)\n"
                "    (pcb_text_width 0.15)\n    (pcb_text_size 0.9 0.9)\n"
                "    (mod_edge_width 0.15)\n    (mod_text_size 0.7 0.7)\n"
                "    (mod_text_width 0.12)\n    (pad_size 1.5 1.5)\n    (pad_drill 1.0)\n"
                "    (pad_to_mask_clearance 0.05)\n    (aux_axis_origin 0 0)\n"
                "    (visible_elements 7FFFFFFF)\n  )\n\n")
    for i, n in enumerate(NETS):
        head.append("  (net %d \"%s\")\n" % (i, n))
    head.append("\n")

    out = "".join(head) + "".join(PARTS) + "".join(segs) + "".join(edges) \
        + "".join(texts) + ")\n"
    OUT.write_text(out, encoding="utf-8")
    print("wrote", OUT, len(out), "bytes")
    print("parts=%d segments=%d texts=%d edges=%d"
          % (len(PARTS), len(segs), len(texts), len(edges)))


if __name__ == "__main__":
    build()
