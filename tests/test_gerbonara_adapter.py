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


@pytest.mark.parametrize("command,expected_bounds,sweep", [
    ("G03", (-0.2, -0.2, 10.2, 10.2), math.pi / 2),
    ("G02", (-10.2, -10.2, 10.2, 10.2), 3 * math.pi / 2),
])
def test_arc_stroke(tmp_path, command, expected_bounds, sweep):
    p = gerber(tmp_path, "%ADD10C,0.4*%\nD10*\nG75*\nX10000000Y0D02*\n"
               f"{command}X0Y10000000I-10000000J0D01*")
    layer = GerbonaraImporter().copper(p, "top")
    poly = Polygon(layer.polygons[0].exterior, layer.polygons[0].holes)
    assert poly.bounds == pytest.approx(expected_bounds, abs=0.003)
    assert poly.area == pytest.approx(10 * sweep * 0.4 + math.pi * 0.2**2, rel=0.002)


def test_full_circle_stroke(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.4*%\nD10*\nG75*\nX10000000Y0D02*\n"
               "G03X10000000Y0I-10000000J0D01*")
    layer = GerbonaraImporter().copper(p, "top")
    assert len(layer.polygons) == 1
    assert len(layer.polygons[0].holes) == 1
    assert area(layer) == pytest.approx(2 * math.pi * 10 * 0.4, rel=0.002)


def test_degenerate_region_reports_port_error(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.1*%\nD10*\nG01*\nG36*\n"
               "X0Y0D02*\nX10000000Y0D01*\nG37*")
    with pytest.raises(PCBImportError):
        GerbonaraImporter().copper(p, "top")


def test_hole_aperture_geometry(tmp_path):
    p = gerber(tmp_path, "%ADD10C,2X1*%\nD10*\nX0Y0D03*")
    layer = GerbonaraImporter().copper(p, "top")
    assert area(layer) == pytest.approx(math.pi * 0.75, rel=2e-4)
    assert len(layer.polygons[0].holes) == 1


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


def rectangle_loop(x, y, w, h):
    def xy(a, b):
        return f"X{round(a*1e6)}Y{round(b*1e6)}"
    corners = [(x, y), (x+w, y), (x+w, y+h), (x, y+h), (x, y)]
    return "G01*\n" + "\n".join(xy(a, b) + ("D02*" if i == 0 else "D01*")
                                    for i, (a, b) in enumerate(corners))


def outline_polygon(path):
    board = GerbonaraImporter().outline(path)
    return Polygon(board.exterior, board.holes)


def test_semicircular_outline(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.2*%\nD10*\nG75*\nG01*\n"
               "X0Y0D02*\nX10000000Y0D01*\nG03X0Y0I-5000000J0D01*")
    shape = outline_polygon(p)
    assert shape.area == pytest.approx(math.pi*25/2, rel=0.001)
    assert shape.bounds == pytest.approx((0, 0, 10, 5), abs=0.002)


def test_circular_cutout(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.2*%\nD10*\n" + rectangle_loop(0, 0, 30, 20)
               + "\nG75*\nG01*\nX17000000Y10000000D02*\n"
               "G03X17000000Y10000000I-2000000J0D01*")
    shape = outline_polygon(p)
    assert len(shape.interiors) == 1
    assert shape.area == pytest.approx(600 - math.pi*4, abs=0.02)
    assert shape.bounds == (0, 0, 30, 20)


def test_multiple_cutouts_order_independent(tmp_path):
    p = gerber(tmp_path, "%ADD10C,0.2*%\nD10*\n" + rectangle_loop(2, 2, 3, 4)
               + "\n" + rectangle_loop(0, 0, 30, 20)
               + "\n" + rectangle_loop(20, 10, 5, 2))
    shape = outline_polygon(p)
    assert len(shape.interiors) == 2
    assert shape.area == 578


@pytest.mark.parametrize("other", [(35, 1, 2, 2), (0, 3, 2, 2), (29, 3, 2, 2)])
def test_reject_disjoint_touching_or_crossing_outline(tmp_path, other):
    p = gerber(tmp_path, "%ADD10C,0.2*%\nD10*\n" + rectangle_loop(0, 0, 30, 20)
               + "\n" + rectangle_loop(*other))
    with pytest.raises(PCBImportError):
        GerbonaraImporter().outline(p)


@pytest.mark.parametrize("other", [(4, 4, 2, 2), (7, 7, 4, 4)])
def test_reject_nested_or_overlapping_cutouts(tmp_path, other):
    p = gerber(tmp_path, "%ADD10C,0.2*%\nD10*\n" + rectangle_loop(0, 0, 30, 20)
               + "\n" + rectangle_loop(2, 2, 7, 7) + "\n" + rectangle_loop(*other))
    with pytest.raises(PCBImportError):
        GerbonaraImporter().outline(p)


def macro_ring_header():
    return "%AMRING*1,1,$1,0,0,0*1,0,$2,0,0,0*%\n%ADD10RING,4X2*%"


def test_parameterized_macro_ring(tmp_path):
    p = gerber(tmp_path, macro_ring_header() + "\nD10*\nX5000000Y6000000D03*")
    layer = GerbonaraImporter().copper(p, "top")
    poly = Polygon(layer.polygons[0].exterior, layer.polygons[0].holes)
    assert poly.area == pytest.approx(3 * math.pi, rel=2e-4)
    assert poly.bounds == pytest.approx((3, 4, 7, 8))
    assert len(poly.interiors) == 1


@pytest.mark.parametrize("macro", [False, True])
def test_transparent_dark_flash_preserves_existing_copper(tmp_path, macro):
    header = macro_ring_header() if macro else "%ADD10C,4X2*%"
    p = gerber(tmp_path, header + "\n%ADD11R,1X1*%\n%LPD*\nD11*\nX0Y0D03*\nD10*\nX0Y0D03*".replace("%LPD*", "%LPD*%"))
    layer = GerbonaraImporter().copper(p, "top")
    assert area(layer) == pytest.approx(3 * math.pi + 1, rel=2e-4)
    assert len(layer.polygons) == 2


@pytest.mark.parametrize("macro", [False, True])
def test_clear_ring_preserves_center_copper(tmp_path, macro):
    header = macro_ring_header() if macro else "%ADD10C,4X2*%"
    p = gerber(tmp_path, header + "\n%ADD11R,10X10*%\n%LPD*%\nD11*\nX0Y0D03*\n%LPC*%\nD10*\nX0Y0D03*")
    layer = GerbonaraImporter().copper(p, "top")
    assert area(layer) == pytest.approx(100 - 3 * math.pi, rel=2e-4)
    assert len(layer.polygons) == 2


def test_disjoint_macro_circles(tmp_path):
    p = gerber(tmp_path, "%AMPAIR*1,1,2,-3,0,0*1,1,2,3,0,0*%\n"
               "%ADD10PAIR*%\nD10*\nX10000000Y20000000D03*")
    layer = GerbonaraImporter().copper(p, "top")
    assert len(layer.polygons) == 2
    assert area(layer) == pytest.approx(2 * math.pi, rel=2e-4)


def test_macro_outline(tmp_path):
    p = gerber(tmp_path, "%AMTRI*4,1,3,0,0,4,0,0,3,0,0,0*%\n"
               "%ADD10TRI*%\nD10*\nX10000000Y20000000D03*")
    layer = GerbonaraImporter().copper(p, "top")
    assert area(layer) == pytest.approx(6)
    assert Polygon(layer.polygons[0].exterior).bounds == (10,20,14,23)


def test_unsupported_thermal_macro(tmp_path):
    p = gerber(tmp_path, "%AMTHERM*7,0,0,4,2,0.5,0*%\n%ADD10THERM*%\nD10*\nX0Y0D03*")
    with pytest.raises(PCBImportError):
        GerbonaraImporter().copper(p, "top")

# Analytic fixtures, independent of the parser's rectangle conversion.
@pytest.mark.parametrize("primitive,bounds", [
    ("20,1,2,0,0,4,0,0", (10,19,14,21)),
    ("20,1,2,0,0,4,0,90", (9,20,11,24)),
    ("21,1,4,2,3,1,90", (8,21,10,25)),
])
def test_macro_rectangular_primitives(tmp_path, primitive, bounds):
    p=gerber(tmp_path, f"%AMRECT*{primitive}*%\\n%ADD10RECT*%\\nD10*\\nX10000000Y20000000D03*".replace("\\n","\n"))
    layer=GerbonaraImporter().copper(p,"bottom")
    poly=Polygon(layer.polygons[0].exterior,layer.polygons[0].holes)
    assert poly.area==pytest.approx(8)
    assert poly.bounds==pytest.approx(bounds,abs=1e-8)


def test_macro_diagonal_vector_line(tmp_path):
    from shapely.geometry import LineString
    p=gerber(tmp_path,"%AMDIAG*20,1,0.8,0,0,3,4,0*%\n%ADD10DIAG*%\nD10*\nX10000000Y20000000D03*")
    layer=GerbonaraImporter().copper(p,"bottom")
    actual=Polygon(layer.polygons[0].exterior,layer.polygons[0].holes)
    expected=LineString([(10,20),(13,24)]).buffer(0.4,cap_style="flat")
    assert actual.symmetric_difference(expected).area<1e-8


def test_rounded_pad_vector_edges(tmp_path):
    from shapely.geometry import box
    # Equivalent geometric construction to a rounded 4 x 2 mm KiCad pad.
    corners=[(-1.5,-0.5),(1.5,-0.5),(1.5,0.5),(-1.5,0.5)]
    outline="4,1,4,"+",".join(str(v) for pt in corners+[corners[0]] for v in pt)+",0"
    circles=[f"1,1,1,{x},{y},0" for x,y in corners]
    edges=[f"20,1,1,{a[0]},{a[1]},{b[0]},{b[1]},0" for a,b in zip(corners,corners[1:]+corners[:1])]
    p=gerber(tmp_path,"%AMROUND*"+"*".join([outline,*circles,*edges])+"*%\n%ADD10ROUND*%\nD10*\nX10000000Y20000000D03*")
    layer=GerbonaraImporter().copper(p,"bottom")
    assert len(layer.polygons)==1
    actual=Polygon(layer.polygons[0].exterior,layer.polygons[0].holes)
    expected=box(8.5,19.5,11.5,20.5).buffer(0.5,quad_segs=64)
    assert actual.symmetric_difference(expected).area<1e-8


def test_macro_diagnostic_names_file_and_type(tmp_path):
    p=gerber(tmp_path,"%AMTHERM*7,0,0,4,2,0.5,0*%\n%ADD10THERM*%\nD10*\nX0Y0D03*")
    with pytest.raises(PCBImportError,match=r"layer\.gbr.*THERM.*Thermal"):
        GerbonaraImporter().copper(p,"top")

@pytest.mark.parametrize("primitive,local,angle", [
    ("21,1,4,2,3,1,30", (1,0,5,2),30),
    ("20,1,2,0,0,4,0,30", (0,-1,4,1),30),
])
def test_macro_nonorthogonal_rotation(tmp_path,primitive,local,angle):
    from shapely import affinity
    from shapely.geometry import box
    p=gerber(tmp_path,f"%AMROT*{primitive}*%\n%ADD10ROT*%\nD10*\nX10000000Y20000000D03*")
    layer=GerbonaraImporter().copper(p,"bottom")
    actual=Polygon(layer.polygons[0].exterior,layer.polygons[0].holes)
    expected=affinity.translate(affinity.rotate(box(*local),angle,origin=(0,0)),10,20)
    assert actual.symmetric_difference(expected).area<1e-8, (actual.wkt,expected.wkt)

def test_kicad_parameterized_roundrect(tmp_path):
    from shapely.geometry import box
    # Generic pad, not a user's actual board; KiCad's optional circle rotation
    # is omitted and the unused final aperture parameter is retained.
    macro = ("%AMRoundRect*\n"
             "4,1,4,$2,$3,$4,$5,$6,$7,$8,$9,$2,$3,0*\n"
             "1,1,$1+$1,$2,$3*\n1,1,$1+$1,$4,$5*\n"
             "1,1,$1+$1,$6,$7*\n1,1,$1+$1,$8,$9*\n"
             "20,1,$1+$1,$2,$3,$4,$5,0*\n"
             "20,1,$1+$1,$4,$5,$6,$7,0*\n"
             "20,1,$1+$1,$6,$7,$8,$9,0*\n"
             "20,1,$1+$1,$8,$9,$2,$3,0*%\n")
    p = gerber(tmp_path, macro + "%ADD10RoundRect,0.3X1.2X0.7X-1.2X0.7X-1.2X-0.7X1.2X-0.7X0*%\n"
               "D10*\nX8000000Y-5000000D03*")
    layer = GerbonaraImporter().copper(p, "bottom")
    assert len(layer.polygons) == 1
    actual = Polygon(layer.polygons[0].exterior, layer.polygons[0].holes)
    expected = box(6.8,-5.7,9.2,-4.3).buffer(0.3,quad_segs=64)
    assert actual.symmetric_difference(expected).area < 1e-8


EMPTY_NPTH = ("M48\n; DRILL file KiCad\n"
              "; #@! TF.FileFunction,NonPlated,1,2,NPTH\n"
              "FMAT,2\nMETRIC\n%\nG90\nG05\nM30\n")


def test_empty_kicad_npth(tmp_path):
    p=tmp_path/"empty.drl"
    p.write_text(EMPTY_NPTH,encoding="ascii")
    layer=GerbonaraImporter().drills(p)
    assert layer.source==str(p)
    assert layer.drills==() and layer.slots==()


@pytest.mark.parametrize("text", [
    "",
    EMPTY_NPTH.replace("M30\n",""),
    EMPTY_NPTH.replace("NonPlated,1,2,NPTH","Plated,1,2,PTH"),
    EMPTY_NPTH.replace("M30","X3.0Y4.0\nM30"),
])
def test_empty_npth_recognition_is_narrow(tmp_path,text):
    from pcb_studio.infrastructure.cam.gerbonara_adapter import _empty_kicad_npth
    p=tmp_path/"invalid.drl"
    p.write_text(text,encoding="ascii")
    assert not _empty_kicad_npth(p)


def test_kicad_two_tools_same_diameter_negative_y(tmp_path):
    p=tmp_path/"plated.drl"
    p.write_text("M48\n; #@! TF.FileFunction,Plated,1,2,PTH\nFMAT,2\nMETRIC\n"
                 "; #@! TA.AperFunction,Plated,PTH,ViaDrill\nT1C0.800\n"
                 "; #@! TA.AperFunction,Plated,PTH,ComponentDrill\nT2C0.800\n"
                 "%\nG90\nG05\nT1\nX4.1Y-3.5\nT2\nX8.2Y-6.7\nM30\n",encoding="ascii")
    layer=GerbonaraImporter().drills(p)
    assert len(layer.drills)==2
    assert [d.center for d in layer.drills]==[(4.1,-3.5),(8.2,-6.7)]
    assert [d.diameter_mm for d in layer.drills]==[0.8,0.8]

def test_kicad_warning_filter_is_specific(tmp_path):
    from types import SimpleNamespace
    from pcb_studio.infrastructure.cam.gerbonara_adapter import _known_kicad_absolute_warning
    p=tmp_path/"plated.drl"
    text=EMPTY_NPTH.replace("NonPlated,1,2,NPTH","Plated,1,2,PTH")
    p.write_text(text,encoding="ascii")
    benign=SimpleNamespace(message='file:10 "G90": G90 header statement found after end of header')
    assert _known_kicad_absolute_warning(p,benign)
    assert not _known_kicad_absolute_warning(p,SimpleNamespace(message="Unknown tool"))
    p.write_text(text.replace("G05","G05\nG91"),encoding="ascii")
    assert not _known_kicad_absolute_warning(p,benign)


def test_panel_opt_in_preserves_separate_boards_and_hole(tmp_path):
    from pcb_studio.domain.pcb import PanelOutline
    p = gerber(tmp_path, "%ADD10C,0.05*%\nD10*\n" +
               "\n".join(rectangle_loop(*r) for r in [(5,-8,10,4),(7,-7,2,1),(-8,-8,10,4)]))
    with pytest.raises(PCBImportError):
        GerbonaraImporter().outline(p)
    panel=GerbonaraImporter(allow_panel=True).outline(p)
    assert isinstance(panel,PanelOutline)
    assert len(panel.boards)==2
    shapes=[Polygon(b.exterior,b.holes) for b in panel.boards]
    assert sorted(s.area for s in shapes)==pytest.approx([38,40])
    assert shapes[0].disjoint(shapes[1])


@pytest.mark.parametrize("other",[(0,3,2,2),(29,3,2,2),(0,0,30,20)])
def test_panel_still_rejects_invalid_intersections(tmp_path,other):
    p=gerber(tmp_path,"%ADD10C,0.05*%\nD10*\n"+rectangle_loop(0,0,30,20)+"\n"+rectangle_loop(*other))
    with pytest.raises(PCBImportError):
        GerbonaraImporter(allow_panel=True).outline(p)


def test_flash_cache_reuses_shape_and_preserves_polarity(tmp_path,monkeypatch):
    from gerbonara import GerberFile
    from pcb_studio.infrastructure.cam.gerbonara_adapter import _flash_geometry
    p=gerber(tmp_path,"%ADD10R,4X2*%\nD10*\nX10000000Y20000000D03*\n%LPC*%\nX15000000Y-5000000D03*")
    objects=GerberFile.open(p).objects
    cache={}
    expected=[_flash_geometry(o) for o in objects]
    actual=[_flash_geometry(o,cache) for o in objects]
    assert len(cache)==1
    for a,b in zip(actual,expected):
        assert a.symmetric_difference(b).area<1e-10
    assert actual[1].bounds==pytest.approx((13,-6,17,-4))
