"""Analytic dimensions and conservative cutout rejection tests."""
import math
import pytest
pytest.importorskip("shapely")
from shapely.geometry import LineString, LinearRing
from pcb_studio.domain.pcb import BoardOutline
from pcb_studio.infrastructure.cam.cutout_preview import Tab, plan_cutout_preview


def rect(x,y,w,h):
    return ((x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y))


BOARD = BoardOutline("board",rect(0,0,30,20))
STOCK = BoardOutline("stock",rect(-5,-5,40,30))
TABS = tuple(Tab(p,2) for p in ((15,0),(30,10),(15,20),(0,10)))


def test_outer_compensation():
    p = plan_cutout_preview(BOARD,STOCK,1)
    [path] = p.exterior_paths
    line = LineString(path)
    assert line.is_ring
    assert line.bounds == pytest.approx((-0.502,-0.502,30.502,20.502))
    assert line.length == pytest.approx(100 + 2*math.pi*0.502, abs=0.001)
    assert not LinearRing(path).is_ccw
    assert not p.manufacturing_ready


def test_four_straight_tabs():
    p = plan_cutout_preview(BOARD,STOCK,1,tabs=TABS)
    assert len(p.exterior_paths) == len(p.tab_gaps) == 4
    cut = sum(LineString(s).length for s in p.exterior_paths)
    gap = sum(LineString(s).length for s in p.tab_gaps)
    assert gap == pytest.approx(12)
    assert cut + gap == pytest.approx(p.exterior_full_length_mm)
    assert all(not LineString(s).is_closed for s in p.exterior_paths)
    print(f"cutout rectangle: full={p.exterior_full_length_mm:.9f}; cut={cut:.9f}; gaps={gap:.9f} mm")


def test_internal_cutout_and_direction():
    board = BoardOutline("board",BOARD.exterior,(rect(12,8,6,4),))
    p = plan_cutout_preview(board,STOCK,1,tabs=TABS)
    [path] = p.internal_paths
    assert LinearRing(path).is_ccw
    assert LineString(path).bounds == pytest.approx((12.502,8.502,17.498,11.498))
    assert LineString(path).length == pytest.approx(15.984)
    print(f"internal cutout: {LineString(path).length:.9f} mm")


def test_reverse_directions():
    board = BoardOutline("board",BOARD.exterior,(rect(12,8,6,4),))
    p = plan_cutout_preview(board,STOCK,1,clockwise=False)
    assert LinearRing(p.exterior_paths[0]).is_ccw
    assert not LinearRing(p.internal_paths[0]).is_ccw


def test_small_hole_rejected():
    board = BoardOutline("board",BOARD.exterior,(rect(12,8,0.8,4),))
    with pytest.raises(ValueError,match="too small"):
        plan_cutout_preview(board,STOCK,1)


def test_insufficient_stock():
    with pytest.raises(ValueError,match="leaves stock"):
        plan_cutout_preview(BOARD,BoardOutline("stock",rect(-0.6,-0.6,31.2,21.2)),1)


@pytest.mark.parametrize("tabs", [
    (Tab((15,0),2),Tab((16,0),2)),
    (Tab((0,0),2),),
    (Tab((15,5),2),),
])
def test_invalid_tab_placement(tabs):
    with pytest.raises(ValueError,match="[Tt]ab"):
        plan_cutout_preview(BOARD,STOCK,1,tabs=tabs)


@pytest.mark.parametrize("diameter,margin", [(0,0.002),(1,0),(float("nan"),0.002)])
def test_invalid_settings(diameter,margin):
    with pytest.raises(ValueError):
        plan_cutout_preview(BOARD,STOCK,diameter,margin_mm=margin)


def test_imported_synthetic_board():
    from pathlib import Path
    pytest.importorskip("gerbonara")
    from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
    folder = Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
    board = GerbonaraImporter().outline(folder/"outline.gbr")
    p = plan_cutout_preview(board,STOCK,1,tabs=TABS)
    assert len(p.exterior_paths) == 4
