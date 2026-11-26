"""Build an offline viewer from the actual synthetic Gerber/Excellon files."""
from pathlib import Path
import sys
from pcb_studio.application.import_project import import_project
from pcb_studio.domain.pcb import BoardOutline
from pcb_studio.domain.tools import CuttingTool, ToolLibrary, ProcessSettings
from pcb_studio.domain.depth import DepthSetup
from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
from pcb_studio.infrastructure.cam.job_preview import plan_job_preview
from pcb_studio.infrastructure.cam.cutout_preview import Tab
from pcb_studio.infrastructure.cam.tool_binding import ToolSelection, bind_job_tools, isolation_tool_spec
from pcb_studio.infrastructure.cam.motion_preview import plan_motion_preview
from pcb_studio.infrastructure.cam.gcode_preview import render_gcode_preview
from pcb_studio.infrastructure.cam.gcode_viewer import viewer_data, render_svg, render_html


def build_demo():
    root=Path(__file__).resolve().parents[1]/"examples"/"synthetic_board"
    project=import_project(GerbonaraImporter(),"Synthetic board 30 x 20 mm",
                           copper_files=((root/"bottom.gbr","bottom"),),
                           drill_files=(root/"drills.drl",),outline_file=root/"outline.gbr")
    lib=ToolLibrary((CuttingTool("v","V","v_bit",3.175,1,0.1,30),
                     CuttingTool("d","D","drill",1,3),
                     CuttingTool("e","E","end_mill",1,3)))
    iso=ToolSelection("v",ProcessSettings(0.1,0.1,30,10000,100))
    drill=ToolSelection("d",ProcessSettings(1.6,0.8,30,10000))
    cut=ToolSelection("e",ProcessSettings(1.6,0.8,30,10000,80))
    stock=BoardOutline("stock",((-5,-5),(35,-5),(35,25),(-5,25),(-5,-5)))
    tabs=tuple(Tab(p,2) for p in ((15,0),(30,10),(15,20),(0,10)))
    job=plan_job_preview(project,stock,isolation_tools=(isolation_tool_spec(lib,iso),),
                         target_width_mm=0.15,cutout_diameter_mm=1,tabs=tabs)
    trace=plan_motion_preview(bind_job_tools(job,lib,(iso,drill,cut)),DepthSetup(1.6,3,0.1),start_xy=(0,0))
    text=render_gcode_preview(trace)
    return viewer_data(trace,text)


if __name__=="__main__":
    data=build_demo()
    out=Path(sys.argv[1])
    out.mkdir(parents=True,exist_ok=True)
    (out/"pcb_viewer.html").write_text(render_html(data),encoding="utf-8")
    (out/"pcb_viewer.svg").write_text(render_svg(data),encoding="utf-8")
    print(f"Viewer exported: {len(data['events'])} events; {data['moves']} motions; bounds={data['bounds']}")
