"""Comment-only offline G-code representation. Never a runnable CNC program."""
from math import isfinite

from pcb_studio.infrastructure.cam.motion_validation import validate_motion_preview


def _number(value):
    if not isfinite(value) or abs(value)>1_000_000:
        raise ValueError("Value outside offline preview numeric range")
    return f"{value:.6f}"


def render_gcode_preview(trace):
    """Render explicit absolute G0/G1 words, inside comments on every line.

    No spindle, tool change, offsets, initialization motion, or streaming.
    START and STAGE are preview metadata, not G-code instructions.
    Six decimals are a serialization convention, not machine resolution.
    """
    validate_motion_preview(trace)
    x,y,z=map(_number,trace.initial_position)
    lines=["OFFLINE ONLY V1","G21","G90","G94",f"START X{x} Y{y} Z{z}"]
    for e in trace.events:
        if e.kind=="tool_setup":
            lines.append(f"STAGE {e.stage_index}")
        elif e.kind in ("rapid_xy","cut_xy"):
            x,y=map(_number,e.end[:2])
            line=f"G0 X{x} Y{y}" if e.kind=="rapid_xy" else (
                f"G1 X{x} Y{y} F{_number(e.feed_mm_min)}")
            lines.append(line)
        elif e.kind=="plunge":
            lines.append(f"G1 Z{_number(e.end[2])} F{_number(e.feed_mm_min)}")
        elif e.kind=="retract":
            lines.append(f"G0 Z{_number(e.end[2])}")
        else:
            raise ValueError("Unsupported event")
    lines.append("END OFFLINE PREVIEW")
    return "".join(";@preview "+line+"\n" for line in lines)
