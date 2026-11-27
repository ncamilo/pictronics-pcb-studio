"""Run the original FlatCAM diameter grouping in its isolated environment."""
import json
import os
from pathlib import Path
from shapely.geometry import Point
from appPlugins.ToolDrilling.DrillingGen import merge_same_diameter_tools, diameter_conflicts


def test_export_drilling():
    case = json.loads(Path(os.environ["PCB_DRILL_CASES"]).read_text())
    tools = {
        t["id"]: {"tooldia": t["diameter"],
                  "drills": [Point(p) for p in t["drills"]],
                  "slots": [(Point(a), Point(b)) for a,b in t["slots"]],
                  "data": {"fixture_plated": t["plated"]}}
        for t in case["tools"]
    }
    conflicts = diameter_conflicts(tools)
    merged = merge_same_diameter_tools(tools)
    output = []
    for t in merged.values():
        d = t["tooldia"]
        for p in t["drills"]:
            output.append(["drill",d,p.x,p.y])
        for a,b in t["slots"]:
            output.append(["mill_slot",d,a.x,a.y,b.x,b.y])
    assert len(conflicts) == 1
    assert conflicts[0][0] == case["expected_conflict_diameter"]
    assert "fixture_plated" in conflicts[0][2]
    Path(os.environ["PCB_DRILL_RESULT"]).write_text(
        json.dumps({"records": sorted(output), "conflicts": conflicts}), encoding="utf-8")
