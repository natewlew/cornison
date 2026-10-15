#!/usr/bin/env python3
"""Turn a build123d-exported DXF (LINE/ARC/CIRCLE primitives, no
guaranteed order) into closed point loops, the same way the earlier
Edge.Cuts outline rebuild chained raw segments: every primitive becomes
one or more graph edges between endpoint nodes (matched by rounding to a
tolerance, not by trusting any original ordering), then each loop is
walked out of that graph. This sidesteps a real ordering bug found in
build123d's own Wire.order_edges() on this geometry (a long straight run
was skipped) -- graph-based reconstruction doesn't depend on any
upstream ordering being correct at all, only on endpoints matching.

Run with the same environment as case.py (needs ezdxf, which build123d
already pulls in):
  uv run --with build123d python3 case/scripts/dxf_to_loops.py <file.dxf>
"""
import math
import sys

import ezdxf

TOL = 1e-4  # mm, endpoint-matching tolerance
ARC_SEGMENT_LEN = 0.5  # mm, max chord length when flattening arcs/circles


def quantize(pt):
    return (round(pt[0] / TOL), round(pt[1] / TOL))


def arc_points(center, radius, start_deg, end_deg):
    span = end_deg - start_deg
    if span <= 0:
        span += 360
    circumference_frac = radius * math.radians(span)
    n = max(2, int(circumference_frac / ARC_SEGMENT_LEN) + 1)
    pts = []
    for i in range(n + 1):
        a = math.radians(start_deg + span * i / n)
        pts.append((center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)))
    return pts


def circle_points(center, radius):
    n = max(8, int(2 * math.pi * radius / ARC_SEGMENT_LEN) + 1)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.append((center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)))
    return pts


def dxf_to_loops(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    open_segments = []  # each: list of (x,y), first != last
    closed_loops = []  # each: list of (x,y), already a complete loop (circles)

    for e in msp:
        t = e.dxftype()
        if t == "LINE":
            s, en = e.dxf.start, e.dxf.end
            open_segments.append([(s.x, s.y), (en.x, en.y)])
        elif t == "ARC":
            c = e.dxf.center
            pts = arc_points((c.x, c.y), e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle)
            open_segments.append(pts)
        elif t == "CIRCLE":
            c = e.dxf.center
            closed_loops.append(circle_points((c.x, c.y), e.dxf.radius))
        elif t == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points("xy")]
            if e.closed:
                closed_loops.append(pts)
            else:
                open_segments.append(pts)
        else:
            raise ValueError(f"unexpected DXF entity type: {t}")

    # ---- chain open_segments into closed loops via a node graph ----
    adjacency = {}  # quantized point -> list of (segment_index, end: 0 or 1)

    def add_node(node, seg_idx, end):
        adjacency.setdefault(node, []).append((seg_idx, end))

    for i, seg in enumerate(open_segments):
        add_node(quantize(seg[0]), i, 0)
        add_node(quantize(seg[-1]), i, 1)

    for node, uses in adjacency.items():
        if len(uses) != 2:
            raise ValueError(
                f"endpoint used {len(uses)} times (expected exactly 2) at node {node} "
                f"-- geometry isn't a clean set of closed loops"
            )

    visited = [False] * len(open_segments)
    for start_idx in range(len(open_segments)):
        if visited[start_idx]:
            continue
        loop = list(open_segments[start_idx])
        visited[start_idx] = True
        cur_end_node = quantize(open_segments[start_idx][-1])
        start_node = quantize(open_segments[start_idx][0])
        while cur_end_node != start_node:
            candidates = [
                (seg_idx, end) for (seg_idx, end) in adjacency[cur_end_node] if not visited[seg_idx]
            ]
            if not candidates:
                raise ValueError(f"loop didn't close: stuck at {cur_end_node}")
            seg_idx, end = candidates[0]
            seg = open_segments[seg_idx]
            visited[seg_idx] = True
            pts = list(reversed(seg)) if end == 1 else list(seg)
            loop.extend(pts[1:])
            cur_end_node = quantize(loop[-1])
        if loop[0] == loop[-1]:
            loop.pop()
        closed_loops.append(loop)

    # ---- classify: the biggest-area loop is the outer boundary ----
    def shoelace_area(pts):
        a = 0.0
        for i in range(len(pts)):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % len(pts)]
            a += x1 * y2 - x2 * y1
        return abs(a) / 2

    closed_loops.sort(key=shoelace_area, reverse=True)
    outer, holes = closed_loops[0], closed_loops[1:]
    return {"outer": outer, "holes": holes}


if __name__ == "__main__":
    result = dxf_to_loops(sys.argv[1])
    print(f"outer: {len(result['outer'])} pts")
    print(f"holes: {len(result['holes'])}")
    for h in result["holes"]:
        print(f"  {len(h)} pts")
