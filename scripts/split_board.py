#!/usr/bin/env python3
"""Split a board joined by mouse-bite / break-off tabs into one .kicad_pcb per piece.

The bridge area of every footprint from the Panelization library (or whose
name contains "MouseBite") is cut out of the board outline, which leaves the
pieces as they are after breaking the tabs. For each piece, a copy of the
board is saved with only that piece's outline and the footprints on it, so
each can be exported to its own STEP file.

Usage: python3 scripts/split_board.py IN.kicad_pcb OUT_PREFIX
Writes OUT_PREFIX0.kicad_pcb (largest piece), OUT_PREFIX1.kicad_pcb, ...
and prints the number of pieces. OUT_PREFIX should sit next to IN so
${KIPRJMOD} model paths still resolve.
"""
import os
import sys

import pcbnew

MIN_AREA_MM2 = 1.0


def is_tab(fp):
    fpid = fp.GetFPIDAsString().lower()
    return fpid.startswith("panelization:") or "mousebite" in fpid


def tab_cut(board):
    """Union of the bridge rectangles: bbox of each tab footprint's Edge.Cuts shapes."""
    cut = pcbnew.SHAPE_POLY_SET()
    for fp in board.GetFootprints():
        if not is_tab(fp):
            continue
        edges = [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.Edge_Cuts]
        if not edges:
            continue
        bb = edges[0].GetBoundingBox()
        for g in edges[1:]:
            bb.Merge(g.GetBoundingBox())
        r = pcbnew.SHAPE_POLY_SET()
        r.NewOutline()
        for x, y in ((bb.GetX(), bb.GetY()), (bb.GetRight(), bb.GetY()),
                     (bb.GetRight(), bb.GetBottom()), (bb.GetX(), bb.GetBottom())):
            r.Append(x, y)
        cut.BooleanAdd(r)
    return cut


def pieces(path):
    board = pcbnew.LoadBoard(path)
    outline = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(outline, False):
        sys.exit("board outline (Edge.Cuts) is not closed")
    outline.BooleanSubtract(tab_cut(board))
    res = []
    for i in range(outline.OutlineCount()):
        one = pcbnew.SHAPE_POLY_SET()
        one.AddOutline(outline.COutline(i))
        for k in range(outline.HoleCount(i)):
            one.AddHole(outline.CHole(i, k))
        area = outline.COutline(i).Area() / 1e12
        if area >= MIN_AREA_MM2:
            res.append((area, one))
    res.sort(key=lambda a: -a[0])
    return res


def write_piece(src, poly, dst):
    board = pcbnew.LoadBoard(src)
    # footprints first: after board.Remove() on drawings, SWIG returns
    # untyped proxies for the footprint list
    outer = poly.COutline(0)
    drop = []
    for fp in board.GetFootprints():
        p = fp.GetPosition()
        c = fp.GetBoundingBox(False).GetCenter()
        inside = outer.PointInside(pcbnew.VECTOR2I(p.x, p.y)) or outer.PointInside(pcbnew.VECTOR2I(c.x, c.y))
        if is_tab(fp) or not inside:
            drop.append(fp)
    for fp in drop:
        board.Remove(fp)
    kept = sorted(fp.GetReference() for fp in board.GetFootprints())
    for d in [d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts]:
        board.Remove(d)
    # new outline: the piece outline plus its holes, as Edge.Cuts polygons
    chains = [poly.COutline(0)] + [poly.CHole(0, k) for k in range(poly.HoleCount(0))]
    for ch in chains:
        ps = pcbnew.SHAPE_POLY_SET()
        ps.AddOutline(ch)
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_POLY)
        s.SetPolyShape(ps)
        s.SetFilled(False)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.05))
        board.Add(s)
    pcbnew.SaveBoard(dst, board)
    return kept


def main(src, prefix):
    import subprocess
    n = len(pieces(src))
    # one child process per piece: KiCad's SWIG proxies go stale after a few
    # LoadBoard/Remove cycles in the same interpreter
    for k in range(n):
        subprocess.run([sys.executable, __file__, "--piece", str(k), src, prefix], check=True)
    print(n)


def main_piece(k, src, prefix):
    area, poly = pieces(src)[k]
    refs = write_piece(src, poly, f"{prefix}{k}.kicad_pcb")
    print(f"piece {k}: {area:.0f} mm2, {len(refs)} footprints: {' '.join(refs)}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--piece":
        main_piece(int(sys.argv[2]), sys.argv[3], sys.argv[4])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        sys.exit(__doc__)
    # skip interpreter teardown: SWIG prints harmless "memory leak" lines
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)
