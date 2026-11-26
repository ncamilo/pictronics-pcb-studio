"""Compare the same synthetic board without importing the FlatCAM application."""
import json
import sys
from dataclasses import asdict
from pathlib import Path

from shapely import from_wkb
from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
from pcb_studio.infrastructure.cam.geometry_comparison import (
    compare_geometry, geometry_from_copper,
)


def main(source, reference_file):
    reference = json.loads(reference_file.read_text(encoding="utf-8"))
    assert reference["units"] == "mm"
    importer = GerbonaraImporter()
    layer = importer.copper(source / "bottom.gbr", "bottom")
    copper = geometry_from_copper(layer)
    metrics = compare_geometry(copper, from_wkb(reference["copper_wkb_hex"]))
    layer = importer.drills(source / "drills.drl")
    drills = sorted([*d.center, d.diameter_mm] for d in layer.drills)
    slots = sorted([*s.start, *s.end, s.diameter_mm] for s in layer.slots)
    print(json.dumps({"geometry": asdict(metrics), "drills": drills, "slots": slots,
                      "reference_drills": reference["drills"],
                      "reference_slots": reference["slots"]}, indent=2))
    # Exploratory thresholds for this specific board, not manufacturing acceptance.
    assert metrics.matching_topology_counts
    assert metrics.symmetric_difference_mm2 <= 0.08
    assert metrics.boundary_hausdorff_mm <= 0.02
    assert metrics.max_bounds_delta_mm <= 0.01
    for actual, expected in ((drills, reference["drills"]), (slots, reference["slots"])):
        assert len(actual) == len(expected)
        for a, b in zip(actual, expected):
            assert len(a) == len(b)
            assert all(abs(x-y) <= 1e-6 for x, y in zip(a, b))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
