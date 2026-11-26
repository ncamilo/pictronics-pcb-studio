"""Compare grouped feature multiplicities independently of route order."""
import json
import sys
from pathlib import Path
from collections import Counter
from pcb_studio.domain.pcb import DrillLayer, Drill, Slot, BoardOutline
from pcb_studio.infrastructure.cam.drilling_preview import plan_drilling_preview


def main(case_file, reference_file):
    case = json.loads(case_file.read_text())
    reference = json.loads(reference_file.read_text())
    layers = [DrillLayer(str(t["id"]),
                        tuple(Drill(tuple(p),t["diameter"],t["plated"]) for p in t["drills"]),
                        tuple(Slot(tuple(a),tuple(b),t["diameter"],t["plated"]) for a,b in t["slots"]))
              for t in case["tools"]]
    board = BoardOutline("fixture", ((0,0),(30,0),(30,20),(0,20),(0,0)))
    plan = plan_drilling_preview(layers, board)
    records = []
    for stage in plan.stages:
        for ref in stage.features:
            f = ref.feature
            coords = f.center if isinstance(f,Drill) else (*f.start,*f.end)
            records.append([stage.operation,stage.diameter_mm,*coords])
    actual = [[s.operation,s.diameter_mm,len(s.features)] for s in plan.stages]
    print(json.dumps({"studio_groups":actual,"flatcam_records":reference["records"],
                      "studio_records":sorted(records),"flatcam_conflicts":reference["conflicts"],
                      "studio_duplicates":len(plan.duplicate_features)}), flush=True)
    assert actual == case["expected"]
    assert Counter(map(tuple,records)) == Counter(map(tuple,reference["records"]))
    [(first,second)] = plan.duplicate_features
    assert first.feature.plated is True and second.feature.plated is False
    assert first.feature.diameter_mm == case["expected_conflict_diameter"]
    # PTH/NPTH provenance is a Studio property, not inferred from FlatCAM's merged data.
    assert sorted((r.source,r.feature.plated) for s in plan.stages for r in s.features) == sorted(
        (str(t["id"]),t["plated"]) for t in case["tools"]
        for _ in range(len(t["drills"])+len(t["slots"])))
    assert not plan.manufacturing_ready


if __name__ == "__main__":
    main(Path(sys.argv[1]),Path(sys.argv[2]))
