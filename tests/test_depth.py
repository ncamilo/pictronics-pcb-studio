import pytest
from pcb_studio.domain.depth import DepthSetup,depth_levels,validate_depth


@pytest.mark.parametrize("depth,step,count",[(1.6,0.8,2),(1.7,0.6,3),(0.1,0.1,1),(0.3,0.1,3)])
def test_depth_levels(depth,step,count):
    levels=depth_levels(depth,step)
    assert len(levels)==count
    assert levels[-1]==-depth
    assert all(0<a-b<=step+1e-12 for a,b in zip((0,)+levels,levels))


@pytest.mark.parametrize("depth,step",[(0,1),(1,0),(1,2),(float("nan"),1),(1,1e-9)])
def test_invalid_depth_levels(depth,step):
    with pytest.raises(ValueError):
        depth_levels(depth,step)


@pytest.mark.parametrize("args",[(0,3,0.1),(1.6,0,0.1),(1.6,3,-0.1),(1.6,float("inf"),0.1)])
def test_invalid_setup(args):
    with pytest.raises(ValueError):
        DepthSetup(*args)


@pytest.mark.parametrize("operation,depth",[
    ("isolation",1.6),("drill",1.5),("cutout_external",1.8),("unknown",0.1)])
def test_depth_rejection(operation,depth):
    with pytest.raises(ValueError):
        validate_depth(operation,depth,DepthSetup(1.6,3,0.1))


def test_depth_limits():
    s=DepthSetup(1.6,3,0.1)
    validate_depth("isolation",0.1,s)
    validate_depth("mill_slot",1.6,s)
    validate_depth("cutout_internal",1.7,s)
