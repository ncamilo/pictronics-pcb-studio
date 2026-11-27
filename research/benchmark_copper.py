"""Synthetic panel benchmark: geometry only, not desktop startup."""
from time import perf_counter
from shapely.geometry import Point,LineString,GeometryCollection
from shapely import union_all
from pcb_studio.infrastructure.cam.copper_composition import compose_copper

def main():
    ops=[]
    for board in range(12):
        x=(board%6)*32
        y=(board//6)*66
        for i in range(42):
            px=x+2+(i%7)*3.5
            py=y+2+(i//7)*9
            ops.append((Point(px,py).buffer(0.8,quad_segs=64),True))
        for i in range(116):
            px=x+2+(i%7)*3.5
            py=y+2+(i//7%6)*9
            ops.append((LineString([(px,py),(px+2,py+1)]).buffer(0.2,quad_segs=64),True))
    start=perf_counter()
    actual=compose_copper(ops)
    elapsed=perf_counter()-start
    # Independent batch oracle; avoid very expensive sequential 12-board overlay.
    expected=union_all([g for g,_ in ops])
    assert actual.symmetric_difference(expected).area<1e-8
    print(f"PERF panel operations={len(ops)} batched_seconds={elapsed:.6f} area={actual.area:.9f}")
if __name__=="__main__":
    main()
