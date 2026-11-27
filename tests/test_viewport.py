import pytest
from pcb_studio.presentation.viewport import Viewport,grid_values,measure

RECT=(20,30,800,500)


def test_roundtrip_and_y_direction():
    v=Viewport((-30,-20,10,20))
    for xy in ((0,0),(-30,-20),(10,20)):
        assert v.world(v.screen(xy,RECT),RECT)==pytest.approx(xy)
    assert v.screen((0,1),RECT)[1]<v.screen((0,0),RECT)[1]


def test_cursor_anchored_zoom_and_clamp():
    v=Viewport((0,0,30,20))
    p=(345,211)
    before=v.world(p,RECT)
    for factor in (2,1e9,1e-12):
        v.zoom_at(p,factor,RECT)
        assert v.world(p,RECT)==pytest.approx(before)
    assert v.zoom==0.25


def test_pan_and_fit():
    v=Viewport((0,0,30,20))
    a=v.screen((5,10),RECT)
    v.translate(40,-23)
    assert v.screen((5,10),RECT)==pytest.approx((a[0]+40,a[1]-23))
    v.zoom_at(a,2,RECT)
    v.fit()
    assert v.screen((5,10),RECT)==pytest.approx(a)


def test_grid_adapts_and_negative_origin():
    v=Viewport((0,0,30,20))
    step=v.grid_step(RECT)
    assert step*v.scale(RECT)>=60
    v.zoom_at((300,200),10,RECT)
    assert v.grid_step(RECT)<step
    assert grid_values(-2.1,2.1,1)==(-2,-1,0,1,2)


def test_measure_signed_deltas():
    assert measure((5,10),(25,10))==(20,0,20)
    assert measure((4,5),(1,1))==(-3,-4,5)
