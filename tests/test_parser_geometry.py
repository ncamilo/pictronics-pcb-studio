"""Synthetic parser object checks; no copper composition or CAM yet."""
import pytest

gerbonara = pytest.importorskip("gerbonara")
GerberFile = gerbonara.GerberFile
ExcellonFile = gerbonara.ExcellonFile


def load_gerber(tmp_path, body):
    path = tmp_path / "geometry.gbr"
    path.write_text("%FSLAX46Y46*%\n%MOMM*%\n" + body + "\nM02*\n", encoding="ascii")
    return GerberFile.open(path)


def bounds(obj):
    lo, hi = obj.bounding_box(unit="mm")
    return (*lo, *hi)


@pytest.mark.parametrize("shape", ["R", "O"])
def test_rectangular_and_obround_flash(tmp_path, shape):
    layer = load_gerber(tmp_path, f"%ADD10{shape},4X2*%\n%LPD*%\nD10*\nX10000000Y20000000D03*")
    assert len(layer.objects) == 1
    assert type(layer.objects[0]).__name__ == "Flash"
    assert bounds(layer.objects[0]) == pytest.approx((8, 19, 12, 21))


def test_straight_stroke(tmp_path):
    layer = load_gerber(tmp_path, "%ADD10C,0.4*%\n%LPD*%\nD10*\n"
                        "G01*\nX10000000Y20000000D02*\nX15000000Y20000000D01*")
    assert len(layer.objects) == 1
    assert type(layer.objects[0]).__name__ == "Line"
    assert bounds(layer.objects[0]) == pytest.approx((9.8, 19.8, 15.2, 20.2))


def test_quarter_arc(tmp_path):
    layer = load_gerber(tmp_path, "%ADD10C,0.4*%\n%LPD*%\nD10*\nG75*\n"
                        "X10000000Y0D02*\nG03X0Y10000000I-10000000J0D01*")
    assert len(layer.objects) == 1
    assert type(layer.objects[0]).__name__ == "Arc"
    assert bounds(layer.objects[0]) == pytest.approx((-0.2, -0.2, 10.2, 10.2), abs=1e-5)


def test_closed_region(tmp_path):
    layer = load_gerber(tmp_path, "%ADD10C,0.1*%\nD10*\n%LPD*%\nG01*\nG36*\n"
                        "X0Y0D02*\nX10000000Y0D01*\nX10000000Y5000000D01*\n"
                        "X0Y5000000D01*\nX0Y0D01*\nG37*")
    assert len(layer.objects) == 1
    assert type(layer.objects[0]).__name__ == "Region"
    assert bounds(layer.objects[0]) == pytest.approx((0, 0, 10, 5))


def test_ordered_polarity(tmp_path):
    layer = load_gerber(tmp_path, "%ADD10C,4*%\n%ADD11C,2*%\n%LPD*%\n"
                        "D10*\nX0Y0D03*\n%LPC*%\nD11*\nX0Y0D03*\n"
                        "%LPD*%\nX0Y0D03*")
    assert [obj.polarity_dark for obj in layer.objects] == [True, False, True]


def test_routed_slot(tmp_path):
    path = tmp_path / "slot.drl"
    path.write_text("M48\nMETRIC,TZ\nT01C0.800\n%\nG90\nT01\n"
                    "G00X10.000Y20.000\nM15\nG01X15.000Y20.000\nM16\nG05\nM30\n",
                    encoding="ascii")
    layer = ExcellonFile.open(path)
    assert len(layer.objects) == 1
    assert type(layer.objects[0]).__name__ == "Line"
    assert bounds(layer.objects[0]) == pytest.approx((9.6, 19.6, 15.4, 20.4))
