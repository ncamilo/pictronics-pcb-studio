"""Strict independent parser for the comment-only offline preview subset."""
from dataclasses import dataclass
from math import isfinite, dist
import re

from pcb_studio.infrastructure.cam.motion_validation import validate_motion_preview

NUM=r"(-?[0-9]{1,7}\.[0-9]{6})"
START=re.compile(r"START X"+NUM+r" Y"+NUM+r" Z"+NUM)
STAGE=re.compile(r"STAGE (0|[1-9][0-9]{0,6})")
GRAMMAR=(
    ("rapid_xy",re.compile(r"G0 X"+NUM+r" Y"+NUM)),
    ("plunge",re.compile(r"G1 Z"+NUM+r" F"+NUM)),
    ("cut_xy",re.compile(r"G1 X"+NUM+r" Y"+NUM+r" F"+NUM)),
    ("retract",re.compile(r"G0 Z"+NUM)),
)
EPS=0.000000501


@dataclass(frozen=True)
class ReadbackEvent:
    kind: str
    stage_index: int
    start: tuple[float,float,float]
    end: tuple[float,float,float]
    feed_mm_min: float | None = None


@dataclass(frozen=True)
class Readback:
    initial: tuple[float,float,float]
    events: tuple[ReadbackEvent,...]


@dataclass(frozen=True)
class RoundtripReport:
    event_count: int
    movement_count: int
    stage_count: int
    max_coordinate_error_mm: float
    max_feed_error_mm_min: float
    collapsed_moves: int
    cutting_xy_mm: float

    @property
    def manufacturing_ready(self):
        return False


def _check(ok,message):
    if not ok:
        raise ValueError(message)


def _values(match):
    values=tuple(float(v) for v in match.groups())
    _check(all(isfinite(v) and abs(v)<=1_000_000 for v in values),"Numeric range")
    return values


def read_gcode_preview(text):
    """Recognize only the offline envelope and explicit supported words.

    Not a general GRBL interpreter. Unwrapped lines and arbitrary commands
    are rejected rather than executed or ignored.
    """
    _check(isinstance(text,str) and len(text)<=100_000_000,"Invalid preview size")
    raw=text.splitlines()
    _check(6<len(raw)<=1_000_006,"Invalid line count")
    prefix=";@preview "
    _check(all(line.startswith(prefix) for line in raw),"Unwrapped preview line")
    lines=[line[len(prefix):] for line in raw]
    _check(lines[:4]==["OFFLINE ONLY V1","G21","G90","G94"]
           and lines[-1]=="END OFFLINE PREVIEW","Invalid envelope or modes")
    m=START.fullmatch(lines[4])
    _check(m is not None,"Missing initial position")
    initial=_values(m)
    pos=initial
    safe=initial[2]
    _check(safe>0,"Invalid initial safe Z")
    stage=-1
    events=[]
    for i,line in enumerate(lines[5:-1],6):
        marker=STAGE.fullmatch(line)
        if marker:
            _check(int(marker[1])==stage+1 and pos[2]==safe,
                   f"Invalid stage marker at line {i}")
            stage+=1
            events.append(ReadbackEvent("tool_setup",stage,pos,pos))
            continue
        _check(stage>=0,"Motion before stage")
        for kind,pattern in GRAMMAR:
            match=pattern.fullmatch(line)
            if match:
                values=_values(match)
                feed=None
                if kind=="rapid_xy":
                    _check(pos[2]==safe,"Rapid XY below safe Z")
                    end=(*values,safe)
                elif kind=="plunge":
                    z,feed=values
                    _check(pos[2]==safe and z<0 and feed>0,"Invalid plunge")
                    end=(*pos[:2],z)
                elif kind=="cut_xy":
                    x,y,feed=values
                    _check(pos[2]<0 and feed>0,"Invalid cutting move")
                    end=(x,y,pos[2])
                else:
                    z,=values
                    _check(pos[2]<0 and z==safe,"Invalid retract")
                    end=(*pos[:2],z)
                events.append(ReadbackEvent(kind,stage,pos,end,feed))
                pos=end
                break
        else:
            raise ValueError(f"Unsupported preview word at line {i}")
    _check(stage>=0 and pos[2]==safe,"Incomplete preview")
    return Readback(initial,tuple(events))


def compare_gcode_preview(trace,text):
    """Compare parsed events to validated source, independently of serialization."""
    validate_motion_preview(trace)
    parsed=read_gcode_preview(text)
    _check(len(parsed.events)==len(trace.events),"Event count mismatch")
    coord_error=max(abs(a-b) for a,b in zip(parsed.initial,trace.initial_position))
    feed_error=0.0
    collapsed=0
    cut=0.0
    for source,actual in zip(trace.events,parsed.events):
        _check((source.kind,source.stage_index)==(actual.kind,actual.stage_index),
               "Event kind or stage mismatch")
        coord_error=max(coord_error,*(abs(a-b) for p,q in
                        ((source.start,actual.start),(source.end,actual.end)) for a,b in zip(p,q)))
        if source.feed_mm_min is None:
            _check(actual.feed_mm_min is None,"Unexpected feed")
        else:
            _check(actual.feed_mm_min is not None,"Missing feed")
            feed_error=max(feed_error,abs(source.feed_mm_min-actual.feed_mm_min))
        if source.start!=source.end and actual.start==actual.end:
            collapsed+=1
        if actual.kind=="cut_xy":
            cut+=dist(actual.start,actual.end)
    _check(coord_error<=EPS and feed_error<=EPS,"Roundtrip numeric mismatch")
    stage_count=sum(e.kind=="tool_setup" for e in parsed.events)
    return RoundtripReport(len(parsed.events),len(parsed.events)-stage_count,stage_count,
                           coord_error,feed_error,collapsed,cut)
