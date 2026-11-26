"""Exploratory parser checks; not production CAM validation."""
import pytest

gerbonara = pytest.importorskip("gerbonara")
from gerbonara.utils import MM

GerberFile = gerbonara.GerberFile
ExcellonFile = gerbonara.ExcellonFile

@pytest.mark.parametrize(
    "units,format_spec,diameter,x,y,expected",
    [
        ("MM", "46", "2", "10000000", "20000000", (9, 19, 11, 21)),
        ("IN", "46", "0.1", "1000000", "2000000", (24.13, 49.53, 26.67, 52.07)),
    ],
)
def test_circle_flash(tmp_path, units, format_spec, diameter, x, y, expected):
    path = tmp_path / "flash.gbr"
    path.write_text(
        f"%FSLAX{format_spec}Y{format_spec}*%\n%MO{units}*%\n"
        f"%ADD10C,{diameter}*%\n%LPD*%\nD10*\nX{x}Y{y}D03*\nM02*\n",
        encoding="ascii",
    )
    layer = GerberFile.open(path)
    assert len(layer.objects) == 1
    lo, hi = layer.bounding_box(unit=MM)
    assert (*lo, *hi) == pytest.approx(expected, abs=1e-6)


def test_excellon_two_holes(tmp_path):
    path = tmp_path / "holes.drl"
    path.write_text(
        "M48\nMETRIC,TZ\nG90\nT01C0.800\n%\nT01\n"
        "X10.000Y20.000\nX15.000Y25.000\nM30\n",
        encoding="ascii",
    )
    layer = ExcellonFile.open(path)
    assert len(layer.objects) == 2
    boxes = [obj.bounding_box(unit=MM) for obj in layer.objects]
    assert (*boxes[0][0], *boxes[0][1]) == pytest.approx((9.6, 19.6, 10.4, 20.4))
    assert (*boxes[1][0], *boxes[1][1]) == pytest.approx((14.6, 24.6, 15.4, 25.4))
