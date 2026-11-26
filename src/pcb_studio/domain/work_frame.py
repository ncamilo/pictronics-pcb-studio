"""Explicit planar work coordinates, independent of machine offsets."""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class WorkFrame:
    origin: tuple[float,float]=(0.0,0.0)
    mirror: str="none"

    def __post_init__(self):
        if (type(self.origin) is not tuple or len(self.origin)!=2
                or any(type(v) not in (float,int) or not isfinite(v) for v in self.origin)
                or self.mirror not in ("none","x","y")):
            raise ValueError("Invalid work frame")

    @property
    def signs(self):
        return (-1 if self.mirror=="x" else 1,-1 if self.mirror=="y" else 1)

    def to_work(self,xy):
        return tuple(s*(v-o) for s,v,o in zip(self.signs,xy,self.origin))

    def to_board(self,xy):
        return tuple(o+s*v for s,v,o in zip(self.signs,xy,self.origin))

    def xyz(self,p):
        return (*self.to_work(p[:2]),p[2])

    def bounds(self,bounds):
        a=self.to_work(bounds[:2])
        b=self.to_work(bounds[2:])
        return (min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1]))


def corner_frame(bounds,mirror="none"):
    """Corner giving nonnegative XY within these bounds after reflection."""
    xmin,ymin,xmax,ymax=bounds
    return WorkFrame((xmax if mirror=="x" else xmin,
                      ymax if mirror=="y" else ymin),mirror)
