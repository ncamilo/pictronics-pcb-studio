"""Analytic preview geometry tests; no machine operations."""
import math
import pytest
pytest.importorskip("gerbonara")
pytest.importorskip("shapely")
from shapely.geometry import Polygon
from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
from pcb_studio.ports.pcb_import import PCBImportError


def gerber(tmp_path, body, units="MM"):
    p = tmp_path / "layer.gbr"
    p.write_text(f"%FSLAX46Y46*%\n%MO{units}*%\n" + body + "\nM02*\n", encoding="ascii")
    return p


def area(layer):
    return sum(Polygon(p.exterior, p.holes).area for p in layer.polygons)


@pytest.mark.parametrize("aperture,expected", [("C,2", math.pi), ("R,4X2", 8),
                                               ("O,4X2", 4+math.pi)])
def test_flash_geometry(tmp_path, aperture, expected):
    p = gerber(tmp_path, f"%ADD10{aperture}*%\n%LPD*%\nD10*\nX10000000Y20000000D03*")
    layer = GerbonaraImporter().copper(p, "bottom")
    assert layer.side == "bottom"
    assert area(layer) == pytest.approx(expected, rel=2e-4)
    poly = Polygon(layer.polygons[0].exterior)
    assert (poly.centroid.x, poly.centroid.y) == pytest.approx((10, 20))


def test_imperial_flash(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.1*%\n%LPD*%\nD10*\nX1000000Y2000000D03*", "IN")
    layer = GerbonaraImporter().copper(p, "top")
    poly = Polygon(layer.polygons[0].exterior)
    assert poly.bounds == pytest.approx((24.13, 49.53, 26.67, 52.07))


def test_stroke_area(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.4*%\nD10*\nG01*\nX0Y0D02*\nX5000000Y0D01*")
    assert area(GerbonaraImporter().copper(p, "top")) == pytest.approx(2+math.pi*0.2**2, rel=2e-4)


def test_region_and_polarity(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.1*%\n%ADD11R,2X2*%\nD10*\nG01*\nG36*\n"
               "X0Y0D02*\nX10000000Y0D01*\nX10000000Y5000000D01*\n"
               "X0Y5000000D01*\nX0Y0D01*\nG37*\n%LPC*%\nD11*\nX5000000Y2500000D03*")
    layer = GerbonaraImporter().copper(p, "top")
    assert area(layer) == pytest.approx(46)
    assert len(layer.polygons[0].holes) == 1


def test_unsupported_arc_fails_closed(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.4*%\nD10*\nG75*\nX10000000Y0D02*\nG03X0Y10000000I-10000000J0D01*")
    with pytest.raises(PCBImportError):
        GerbonaraImporter().copper(p, "top")


def test_hole_aperture_not_silently_filled(tmp_path):
    p = gerber(tmp_path, "%ADD10C,2X1*%\nD10*\nX0Y0D03*")
    with pytest.raises(PCBImportError):
        GerbonaraImporter().copper(p, "top")


@pytest.mark.parametrize("closed", [True, False])
def test_outline_uses_centerline(tmp_path, closed):
    body = ("%ADD10C,0.2*%\nD10*\nG01*\nX0Y0D02*\nX10000000Y0D01*\n"
            "X10000000Y5000000D01*\nX0Y5000000D01*")
    p = gerber(tmp_path, body + ("\nX0Y0D01*" if closed else ""))
    if not closed:
        with pytest.raises(PCBImportError):
            GerbonaraImporter().outline(p)
    else:
        outline = GerbonaraImporter().outline(p)
        assert Polygon(outline.exterior).area == 50


def test_drill_and_slot(tmp_path):
    p = tmp_path / "layer.drl"
    p.write_text("M48\nMETRIC,TZ\nG90\nT01C0.800\n%\nT01\nX10.000Y20.000\n"
                 "G00X15.000Y20.000\nM15\nG01X20.000Y20.000\nM16\nG05\nM30\n",
                 encoding="ascii")
    layer = GerbonaraImporter().drills(p)
    assert len(layer.drills) == len(layer.slots) == 1
    assert layer.drills[0].center == (10, 20)
    assert layer.drills[0].diameter_mm == pytest.approx(0.8)
    assert layer.slots[0].start == (15, 20)
    assert layer.slots[0].end == (20, 20)
    assert layer.slots[0].diameter_mm == pytest.approx(0.8)
