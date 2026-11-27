import pytest
from pcb_studio.domain.work_frame import WorkFrame,corner_frame


@pytest.mark.parametrize("mirror,expected",[
    ("none",(3,4)),("x",(-3,4)),("y",(3,-4))])
def test_inverse_and_z(mirror,expected):
    f=WorkFrame((10,-20),mirror)
    assert f.to_work((13,-16))==expected
    assert f.to_board(expected)==(13,-16)
    assert f.xyz((13,-16,-0.1))==(*expected,-0.1)


@pytest.mark.parametrize("mirror",["none","x","y"])
def test_positive_corner(mirror):
    bounds=(100,-50,160.8,-22.9)
    f=corner_frame(bounds,mirror)
    assert f.bounds(bounds)==pytest.approx((0,0,60.8,27.1))
    assert f.to_work(f.origin)==(0,0)


@pytest.mark.parametrize("origin,mirror",[
    ((float("nan"),0),"none"),((0,0),"xy"),((0,),"none")])
def test_invalid(origin,mirror):
    with pytest.raises(ValueError):
        WorkFrame(origin,mirror)
