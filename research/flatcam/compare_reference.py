"""Compare a synthetic fixture without importing the FlatCAM application."""
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

from shapely import from_wkb
from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
from pcb_studio.infrastructure.cam.geometry_comparison import (
    compare_geometry, geometry_from_copper,
)


def canonical_slots(records):
    # Compare slot geometry without imposing a travel direction on the parser.
    result = []
    for x1, y1, x2, y2, diameter in records:
        start, end = sorted(((x1, y1), (x2, y2)))
        result.append([*start, *end, diameter])
    return sorted(result)


def assert_records(actual, expected):
    assert len(actual) == len(expected), (actual, expected)
    for a, b in zip(actual, expected):
        assert len(a) == len(b)
        assert all(math.isclose(x, y, abs_tol=1e-6, rel_tol=0)
                   for x, y in zip(a, b)), (a, b)


def main(source, reference_file):
    reference = json.loads(reference_file.read_text(encoding="utf-8"))
    assert reference["units"] == "mm"
    importer = GerbonaraImporter()
    copper = geometry_from_copper(importer.copper(source / "bottom.gbr", "bottom"))
    ref_shape = from_wkb(reference["copper_wkb_hex"])
    metrics = compare_geometry(copper, ref_shape)
    layer = importer.drills(source / "drills.drl")
    drills = sorted([*d.center, d.diameter_mm] for d in layer.drills)
    slots = canonical_slots([*s.start, *s.end, s.diameter_mm] for s in layer.slots)
    ref_drills = sorted(reference["drills"])
    ref_slots = canonical_slots(reference["slots"])
    print(json.dumps({"fixture": source.name, "geometry": asdict(metrics),
                      "drills": drills, "slots": slots,
                      "reference_drills": ref_drills, "reference_slots": ref_slots},
                     indent=2), flush=True)
    expected_file = source / "expected.json"
    expected = json.loads(expected_file.read_text(encoding="utf-8")) if expected_file.exists() else None
    # Independent analytical oracle, applied to both parsers.
    if expected is not None:
        for label, shape, count, holes in (
            ("studio", copper, metrics.candidate_components, metrics.candidate_holes),
            ("flatcam", ref_shape, metrics.reference_components, metrics.reference_holes),
        ):
            assert abs(shape.area - expected["area_mm2"]) <= expected["area_tolerance_mm2"], label
            assert count == expected["components"], label
            assert holes == expected["holes"], label
            assert all(abs(x-y) <= expected["bounds_tolerance_mm"]
                       for x, y in zip(shape.bounds, expected["bounds"])), label
        for records in (drills, ref_drills):
            assert_records(records, expected["drills"])
        for records in (slots, ref_slots):
            assert_records(records, canonical_slots(expected["slots"]))
    # Case-specific research thresholds, not machining certification.
    assert metrics.matching_topology_counts
    assert metrics.symmetric_difference_mm2 <= (expected["symdiff_limit_mm2"] if expected else 0.08)
    assert metrics.boundary_hausdorff_mm <= (expected["hausdorff_limit_mm"] if expected else 0.02)
    assert metrics.max_bounds_delta_mm <= (expected["bounds_tolerance_mm"] if expected else 0.01)
    assert_records(drills, ref_drills)
    assert_records(slots, ref_slots)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
