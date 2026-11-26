from pathlib import Path
import pytest

from pcb_studio.application.import_project import import_project
from pcb_studio.domain.pcb import CopperLayer
from pcb_studio.ports.pcb_import import PCBImportError


class FakeImporter:
    def copper(self, path, side):
        return CopperLayer(str(path), side, ())

    def drills(self, path):
        raise PCBImportError("Invalid drill layer")


def test_import_project_via_port():
    project = import_project(FakeImporter(), "Test", copper_files=((Path("board.gbr"), "bottom"),))
    assert project.copper[0].side == "bottom"
    assert not project.manufacturing_ready


def test_import_project_rejects_duplicate_sides():
    with pytest.raises(ValueError):
        import_project(FakeImporter(), "Test", copper_files=((Path("a"), "top"), (Path("b"), "top")))


def test_import_project_propagates_layer_failure():
    with pytest.raises(PCBImportError):
        import_project(FakeImporter(), "Test", copper_files=((Path("a"), "top"),),
                       drill_files=(Path("invalid"),))


def test_synthetic_board_integration():
    pytest.importorskip("gerbonara")
    pytest.importorskip("shapely")
    from shapely.geometry import Point, Polygon
    from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter

    folder = Path(__file__).resolve().parents[1] / "examples" / "synthetic_board"
    project = import_project(GerbonaraImporter(), "Synthetic board",
                             copper_files=((folder / "bottom.gbr", "bottom"),),
                             drill_files=(folder / "drills.drl",),
                             outline_file=folder / "outline.gbr")
    outline = Polygon(project.outline.exterior)
    assert outline.bounds == (0, 0, 30, 20)
    assert outline.area == 600
    assert len(project.copper[0].polygons) == 1
    poly = project.copper[0].polygons[0]
    copper = Polygon(poly.exterior, poly.holes)
    assert copper.bounds == pytest.approx((3.5, 8.5, 26.5, 11.5))
    assert outline.covers(copper)
    drills = project.drills[0].drills
    assert tuple(d.center for d in drills) == ((5, 10), (25, 10))
    for drill in drills:
        assert drill.diameter_mm == pytest.approx(1)
        assert copper.covers(Point(drill.center).buffer(0.5))
    assert not project.manufacturing_ready
