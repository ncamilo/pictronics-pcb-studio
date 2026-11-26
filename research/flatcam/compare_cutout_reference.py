"""Compare canonical XY cutout paths and tab interruptions, not machine jobs."""
import json
import math
import sys
from pathlib import Path

from shapely import from_wkb
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from pcb_studio.domain.pcb import BoardOutline
from pcb_studio.infrastructure.cam.cutout_preview import Tab, plan_cutout_preview


def ring(coords):
    return tuple(tuple(p) for p in coords)


def metrics(actual, expected, radius):
    a, b = unary_union(actual), unary_union(expected)
    if not actual or not expected:
        assert not actual and not expected
        return {"studio_length_mm":0, "flatcam_length_mm":0,
                "hausdorff_mm":0, "swept_difference_mm2":0}
    sa = unary_union([p.buffer(radius,quad_segs=64) for p in actual])
    sb = unary_union([p.buffer(radius,quad_segs=64) for p in expected])
    return {"studio_length_mm":a.length,"flatcam_length_mm":b.length,
            "hausdorff_mm":a.hausdorff_distance(b),
            "swept_difference_mm2":sa.symmetric_difference(sb).area}


def main(case_file, result_file):
    data=json.loads(case_file.read_text())
    refs=json.loads(result_file.read_text())
    assert [c["name"] for c in data["cases"]] == [r["name"] for r in refs]
    stock=BoardOutline("stock",ring(data["stock"]))
    for c,r in zip(data["cases"],refs):
        board=BoardOutline(c["name"],ring(c["outer"]),tuple(ring(h) for h in c["holes"]))
        dia=c["diameter"]
        tabs=tuple(Tab(tuple(p),data["tab_width"]) for p in c["anchors"])
        if c.get("reject"):
            assert r["inner_counts"] == [0]
            try:
                plan_cutout_preview(board,stock,dia,tabs=tabs,margin_mm=data["margin"])
            except ValueError as exc:
                assert "too small" in str(exc)
                print(json.dumps({"case":c["name"],"flatcam_empty_inner":True,
                                  "studio_rejected":str(exc)}),flush=True)
                continue
            raise AssertionError("Studio accepted an inaccessible inner cutout")
        p=plan_cutout_preview(board,stock,dia,tabs=tabs,margin_mm=data["margin"])
        actuals=[p.exterior_paths,p.internal_paths,p.tab_gaps]
        report={"case":c["name"]}
        for label,coords in zip(("external","internal","gaps"),actuals):
            actual=[LineString(q) for q in coords]
            expected=[from_wkb(s) for s in r[label]]
            report[label]=metrics(actual,expected,dia/2)
        print(json.dumps(report),flush=True)
        for label in ("external","internal","gaps"):
            m=report[label]
            # FlatCAM uses its default 16 segments/quadrant here, Studio 64.
            assert abs(m["studio_length_mm"]-m["flatcam_length_mm"]) <= 0.01
            assert m["hausdorff_mm"] <= 0.002
            assert m["swept_difference_mm2"] <= 0.02
        assert len(p.internal_paths)==len(c["holes"])
        assert len(p.tab_gaps)==len(tabs)
        gap_length=sum(LineString(q).length for q in p.tab_gaps)
        assert math.isclose(gap_length,len(tabs)*(data["tab_width"]+dia),abs_tol=1e-8)
        assert math.isclose(sum(LineString(q).length for q in p.exterior_paths)+gap_length,
                            p.exterior_full_length_mm,abs_tol=1e-8)
        for tab in tabs:
            # On this rectangle, the reference and candidate gaps have
            # identical straight-edge anchors (up to the offset distance).
            for paths in (p.tab_gaps,[from_wkb(s).coords for s in r["gaps"]]):
                assert math.isclose(min(Point(tab.anchor).distance(LineString(q)) for q in paths),
                                    dia/2+data["margin"],abs_tol=1e-8)
        assert not p.manufacturing_ready


if __name__=="__main__":
    main(Path(sys.argv[1]),Path(sys.argv[2]))
