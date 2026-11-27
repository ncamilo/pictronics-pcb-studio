"""Invertible display transform in millimetres."""
from dataclasses import dataclass
from math import ceil, floor, hypot, log10, isfinite


@dataclass
class Viewport:
    bounds: tuple[float,float,float,float]
    zoom: float = 1.0
    pan: tuple[float,float] = (0.0,0.0)

    def scale(self, rect):
        _,_,w,h=rect
        xmin,ymin,xmax,ymax=self.bounds
        return min(max(w,1)/max(xmax-xmin,1e-9),
                   max(h,1)/max(ymax-ymin,1e-9))*self.zoom

    def screen(self, xy, rect):
        x,y,w,h=rect
        xmin,ymin,xmax,ymax=self.bounds
        s=self.scale(rect)
        return (x+w/2+self.pan[0]+(xy[0]-(xmin+xmax)/2)*s,
                y+h/2+self.pan[1]-(xy[1]-(ymin+ymax)/2)*s)

    def world(self, pixel, rect):
        x,y,w,h=rect
        xmin,ymin,xmax,ymax=self.bounds
        s=self.scale(rect)
        return ((xmin+xmax)/2+(pixel[0]-x-w/2-self.pan[0])/s,
                (ymin+ymax)/2-(pixel[1]-y-h/2-self.pan[1])/s)

    def zoom_at(self, pixel, factor, rect):
        if not isfinite(factor) or factor<=0:
            raise ValueError("Invalid zoom factor")
        anchor=self.world(pixel,rect)
        self.zoom=min(128.0,max(0.25,self.zoom*factor))
        after=self.screen(anchor,rect)
        self.translate(pixel[0]-after[0],pixel[1]-after[1])

    def translate(self, dx, dy):
        self.pan=(self.pan[0]+dx,self.pan[1]+dy)

    def fit(self):
        self.zoom=1.0
        self.pan=(0.0,0.0)

    def grid_step(self,rect):
        target=60/self.scale(rect)
        power=10**floor(log10(target))
        return next(v*power for v in (1,2,5,10) if v*power>=target)


def grid_values(lo,hi,step):
    first,last=ceil(lo/step),floor(hi/step)
    if last-first>1000:
        return ()
    return tuple(i*step for i in range(first,last+1))


def measure(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    return dx,dy,hypot(dx,dy)
