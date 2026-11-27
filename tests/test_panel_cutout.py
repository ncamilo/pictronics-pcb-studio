import pytest
pytest.importorskip("shapely")
from pcb_studio.domain.pcb import BoardOutline,PanelOutline,Drill,DrillLayer
from pcb_studio.infrastructure.cam.cutout_preview import plan_cutout_preview,Tab
from pcb_studio.infrastructure.cam.drilling_preview import plan_drilling_preview
from pcb_studio.infrastructure.cam.tab_layout import preset_anchors


def rect(x,y,w,h):
    return BoardOutline("synthetic",((x,y),(x+w,y),(x+w,y+h),(x,y+h),(x,y)))


def test_panel_cutout_and_global_drilling():
    panel=PanelOutline("panel",(rect(0,0,10,6),rect(14,0,10,6)))
    stock=rect(-3,-3,30,12)
    tabs=tuple(Tab(a,2) for a in preset_anchors(panel,"four"))
    result=plan_cutout_preview(panel,stock,1,tabs=tabs)
    assert len(result.tab_gaps)==8
    assert len(result.exterior_paths)==8
    drill=plan_drilling_preview((DrillLayer("d",(Drill((5,3),.8),Drill((19,3),.8))),),panel)
    assert len(drill.stages)==1 and len(drill.stages[0].features)==2
    with pytest.raises(ValueError,match="outside board"):
        plan_drilling_preview((DrillLayer("d",(Drill((12,3),.8),)),),panel)


def test_close_boards_and_invalid_anchor_rejected():
    panel=PanelOutline("panel",(rect(0,0,10,6),rect(11.5,0,10,6)))
    stock=rect(-3,-3,30,12)
    with pytest.raises(ValueError,match="clearance|intersects"):
        plan_cutout_preview(panel,stock,1)
    with pytest.raises(ValueError,match="exactly one"):
        plan_cutout_preview(panel,stock,1,tabs=(Tab((10.75,3),2),))
