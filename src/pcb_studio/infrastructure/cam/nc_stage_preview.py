"""Standalone NC files for offline visualization, never approved for execution."""
from dataclasses import asdict, replace
from pcb_studio.domain.work_frame import WorkFrame
import json
from pathlib import Path
import re
import shutil
import tempfile

from pcb_studio.domain.tools import CuttingTool, ToolLibrary
from pcb_studio.infrastructure.cam.tool_binding import ToolSelection, bind_job_tools
from pcb_studio.infrastructure.cam.motion_preview import plan_motion_preview
from pcb_studio.infrastructure.cam.gcode_preview import render_gcode_preview
from pcb_studio.infrastructure.cam.gcode_readback import (
    EPS, compare_gcode_preview, read_gcode_preview,
)

HEADER = "(OFFLINE PREVIEW ONLY - DO NOT RUN ON CNC)"
FOOTER = "(END OFFLINE PREVIEW)"


def _fmt(v):
    return f"{v:.6f}"


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def verify_stage_nc(text, source):
    """Read actual active NC words via the existing strict subset parser.

    The only extra moves are the initial nominal Z and XY positioning.
    No arbitrary comments, modal shortcuts, spindle or controller commands.
    Initial physical machine position is not modeled.
    """
    lines=text.splitlines()
    _require(len(lines)>7 and lines[:4]==[HEADER,"G21","G90","G94"]
             and lines[-1]==FOOTER,"Invalid NC preview envelope")
    z=re.fullmatch(r"G0 Z(-?\d{1,7}\.\d{6})",lines[4])
    xy=re.fullmatch(r"G0 X(-?\d{1,7}\.\d{6}) Y(-?\d{1,7}\.\d{6})",lines[5])
    _require(z is not None and xy is not None,"Invalid initial positioning")
    payload=["OFFLINE ONLY V1","G21","G90","G94",
             f"START X{xy[1]} Y{xy[2]} Z{z[1]}","STAGE 0",*lines[6:-1],
             "END OFFLINE PREVIEW"]
    parsed=read_gcode_preview("".join(";@preview "+line+"\n" for line in payload))
    events=parsed.events[1:]
    _require(bool(source) and len(events)==len(source),"NC movement count mismatch")
    _require(all(abs(a-b)<=EPS for a,b in zip(parsed.initial,source[0].start)),
             "NC initial coordinate mismatch")
    collapsed=0
    for actual,expected in zip(events,source):
        _require(actual.kind==expected.kind,"NC event mismatch")
        _require(all(abs(a-b)<=EPS for p,q in ((actual.start,expected.start),
                 (actual.end,expected.end)) for a,b in zip(p,q)),"NC coordinate mismatch")
        _require((actual.feed_mm_min is None and expected.feed_mm_min is None) or
                 (actual.feed_mm_min is not None and expected.feed_mm_min is not None and
                  abs(actual.feed_mm_min-expected.feed_mm_min)<=EPS),"NC feed mismatch")
        collapsed+=int(expected.start!=expected.end and actual.start==actual.end)
    return {"movements":len(events),"collapsed_moves":collapsed}


def build_stage_nc(job, setup, settings, *, start_xy, frame=WorkFrame()):
    """Use virtual cylindrical tools at planned effective diameters.

    No physical tool dimensions are inferred. Requested RPM is metadata only.
    Each file uses the same work frame. Reflection reverses cutting orientation.
    """
    _require(isinstance(frame,WorkFrame),"Invalid work frame")
    settings=tuple(settings)
    _require(len(settings)==len(job.stages),"One process setting per stage")
    tools=tuple(CuttingTool(f"virtual-{i}","Virtual preview tool",
                 "drill" if s.operation=="drill" else "end_mill",
                 s.diameter_mm,p.depth_mm) for i,(s,p) in enumerate(zip(job.stages,settings)))
    bound=bind_job_tools(job,ToolLibrary(tools),tuple(
        ToolSelection(t.tool_id,p) for t,p in zip(tools,settings)))
    trace=plan_motion_preview(bound,setup,start_xy=start_xy)
    commented=render_gcode_preview(trace)
    report=compare_gcode_preview(trace,commented)
    # Validate canonical trace, then transform full-precision events.
    sources=[[] for _ in job.stages]
    for event in trace.events:
        if event.kind!="tool_setup":
            sources[event.stage_index].append(replace(event,start=frame.xyz(event.start),
                                                       end=frame.xyz(event.end)))
    stem=re.sub(r"[^A-Za-z0-9_-]+","_",job.project_name).strip("_")[:60] or "PCB"
    files={}
    manifest=[]
    for i,(s,events,p) in enumerate(zip(job.stages,sources,settings)):
        # Initial rapid from the previous stage is replaced by explicit entry.
        if events and events[0].kind=="rapid_xy":
            events=events[1:]
        _require(bool(events) and events[0].kind=="plunge","Missing stage entry")
        lines=[]
        for e in events:
            x,y,z=e.end
            if e.kind=="rapid_xy":
                lines.append(f"G0 X{_fmt(x)} Y{_fmt(y)}")
            elif e.kind=="cut_xy":
                lines.append(f"G1 X{_fmt(x)} Y{_fmt(y)} F{_fmt(e.feed_mm_min)}")
            elif e.kind=="plunge":
                lines.append(f"G1 Z{_fmt(z)} F{_fmt(e.feed_mm_min)}")
            elif e.kind=="retract":
                lines.append(f"G0 Z{_fmt(z)}")
            else:
                raise ValueError("Unexpected motion")
        x,y,z=events[0].start
        nc="\n".join([HEADER,"G21","G90","G94",f"G0 Z{_fmt(z)}",
                      f"G0 X{_fmt(x)} Y{_fmt(y)}",*lines,FOOTER])+"\n"
        check=verify_stage_nc(nc,events)
        name=f"{stem}_{job.copper_side}_{i+1:02d}_{s.operation}_{s.diameter_mm:g}mm.preview.nc"
        files[name]=nc
        manifest.append({"file":name,"operation":s.operation,"diameter_mm":s.diameter_mm,
                         "settings":asdict(p),
                         "bounds_xy":[min(q[0] for e in events for q in (e.start,e.end)),
                                      min(q[1] for e in events for q in (e.start,e.end)),
                                      max(q[0] for e in events for q in (e.start,e.end)),
                                      max(q[1] for e in events for q in (e.start,e.end))],**check})
    files["README.txt"]=(
        "OFFLINE VISUALIZATION ONLY. DO NOT RUN THESE FILES ON A CNC.\n"
        "Active G0/G1 moves are for offline viewers such as bCNC. No spindle or tool change.\n"
        "Virtual tools, explicit work XY transform in manifest, no controller offset, no collision check.\n"
        "Do not combine top and bottom jobs or use the values as machining recommendations.\n"
    )
    files["manifest.json"]=json.dumps({
        "manufacturing_ready":False,"format":"offline-stage-nc-preview",
        "side":job.copper_side,"coordinate_system":"work XY from canonical board XY",
        "work_frame":asdict(frame),"cut_direction_reversed":frame.mirror!="none",
        "virtual_tools":True,"spindle_commands":False,"setup":asdict(setup),
        "source_roundtrip_collapsed_moves":report.collapsed_moves,
        "diagnostics":[asdict(d) for d in job.diagnostics],"stages":manifest,
    },indent=2,allow_nan=False)+"\n"
    return files


def export_stage_nc(directory, job, setup, settings, *, start_xy, frame=WorkFrame()):
    # Validate and construct every file before writing anything.
    files=build_stage_nc(job,setup,settings,start_xy=start_xy,frame=frame)
    folder=Path(tempfile.mkdtemp(prefix="pcb-nc-preview-",dir=directory))
    try:
        for name,content in files.items():
            (folder/name).write_text(content,encoding="ascii" if name.endswith(".nc") else "utf-8")
    except Exception:
        shutil.rmtree(folder)
        raise
    return folder
