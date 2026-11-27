"""Compare identical input geometry and separately report the native offset effect."""
import json
import math
import sys
from pathlib import Path

from shapely import from_wkb
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from pcb_studio.infrastructure.cam.isolation_preview import generate_isolation_preview


def swept(paths, radius):
    return unary_union([p.buffer(radius, quad_segs=64) for p in paths])


def main(cases_file, reference_file):
    cases = json.loads(cases_file.read_text())
    refs = json.loads(reference_file.read_text())
    assert [c["name"] for c in cases] == [r["name"] for r in refs]
    for case, ref in zip(cases, refs):
        copper = from_wkb(ref["copper_wkb_hex"])
        dia = case["diameter"]
        preview = generate_isolation_preview(copper, box(0, 0, 20, 20), dia,
                                             passes=case["passes"], overlap=case["overlap"])
        assert len(preview) == len(ref["passes"]) == case["passes"]
        for p, r, expected_count in zip(preview, ref["passes"], case["counts"]):
            actual = [LineString(path) for path in p.paths]
            matched = [from_wkb(s) for s in r["matched"]]
            native = [from_wkb(s) for s in r["native"]]
            a, b, n = map(unary_union, (actual, matched, native))
            sa, sb, sn = (swept(paths, dia/2) for paths in (actual, matched, native))
            metrics = {
                "case": case["name"], "pass": p.index,
                "studio_offset_mm": p.offset_mm,
                "flatcam_native_offset_mm": r["native_offset_mm"],
                "studio_length_mm": a.length, "flatcam_matched_length_mm": b.length,
                "flatcam_native_length_mm": n.length,
                "matched_hausdorff_mm": a.hausdorff_distance(b),
                "native_hausdorff_mm": a.hausdorff_distance(n),
                "matched_swept_difference_mm2": sa.symmetric_difference(sb).area,
                "native_swept_difference_mm2": sa.symmetric_difference(sn).area,
                "studio_rings": len(actual), "matched_rings": len(matched),
                "native_rings": len(native),
                "studio_copper_intersection_mm2": sa.intersection(copper).area,
                "native_copper_intersection_mm2": sn.intersection(copper).area,
            }
            if "probe" in case:
                point = Point(*case["probe"])
                metrics["studio_probe_covered"] = sa.covers(point)
                metrics["matched_probe_covered"] = sb.covers(point)
                metrics["native_probe_covered"] = sn.covers(point)
            print(json.dumps(metrics), flush=True)
            assert math.isclose(p.offset_mm, r["matched_offset_mm"], abs_tol=1e-12)
            assert len(actual) == len(matched) == expected_count
            assert all(path.is_ring for path in actual + matched)
            assert abs(a.length-b.length) <= 1e-6
            assert metrics["matched_hausdorff_mm"] <= 1e-6
            assert metrics["matched_swept_difference_mm2"] <= 1e-6
            assert metrics["studio_copper_intersection_mm2"] <= 1e-9
            if "probe" in case:
                assert metrics["studio_probe_covered"] == metrics["matched_probe_covered"] == case["probe_covered"]
            # Native differences are reported, not treated as failures: the
            # offsets differ intentionally. No physical safety inference.


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
