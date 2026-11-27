"""Export the existing synthetic board demonstration."""
from pathlib import Path
import sys
from pcb_studio.infrastructure.cam.demo import build_demo as load_demo
from pcb_studio.infrastructure.cam.gcode_viewer import render_svg, render_html


def build_demo():
    return load_demo(Path(__file__).resolve().parents[1]/"examples"/"synthetic_board")


if __name__=="__main__":
    data=build_demo()
    out=Path(sys.argv[1])
    out.mkdir(parents=True,exist_ok=True)
    (out/"pcb_viewer.html").write_text(render_html(data),encoding="utf-8")
    (out/"pcb_viewer.svg").write_text(render_svg(data),encoding="utf-8")
    print(f"Viewer exported: {len(data['events'])} events; {data['moves']} motions; bounds={data['bounds']}")
