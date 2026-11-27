"""Offline planar CAM exchange; not machine instructions."""
from dataclasses import replace
from math import isfinite
from pcb_studio.domain.pcb import BoardOutline
from pcb_studio.infrastructure.cam.multi_tool_preview import ToolSpec
from pcb_studio.infrastructure.cam.cutout_preview import Tab
from pcb_studio.infrastructure.cam.job_preview import plan_job_preview


def plan_geometry_job(project, *, side, diameter, target, passes, overlap, cutter,
                 stock_margin, tab_anchors=(), tab_width=2.0):
    """Choose one side without mirroring; model assumed rectangular stock."""
    layers=tuple(layer for layer in project.copper if layer.side==side)
    if len(layers)!=1 or project.outline is None:
        raise ValueError("Select one imported copper side and supply an outline")
    stock=assumed_stock(project.outline,stock_margin)
    xs,ys=zip(*stock.exterior)
    x0,y0,x1,y1=min(xs),min(ys),max(xs),max(ys)
    tabs=tuple(Tab(tuple(xy),tab_width) for xy in tab_anchors)
    job=plan_job_preview(replace(project,copper=layers),stock,
                         isolation_tools=(ToolSpec(diameter,passes,overlap),),
                         target_width_mm=target,cutout_diameter_mm=cutter,tabs=tabs)
    stages=[]
    for s in job.stages:
        if s.operation=="isolation":
            paths=[r.coordinates for r in job.isolation.stages[s.source_index].rings]
            features=[]
        elif s.operation in ("drill","mill_slot"):
            refs=job.drilling.stages[s.source_index].features
            paths=[(r.feature.center,) if s.operation=="drill" else (r.feature.start,r.feature.end) for r in refs]
            features=[{"layer_index":r.layer_index,"feature_index":r.feature_index,
                       "plated":r.feature.plated} for r in refs]
        else:
            paths=job.cutout.internal_paths if s.operation=="cutout_internal" else job.cutout.exterior_paths
            features=[]
        stages.append({"operation":s.operation,"diameter_mm":s.diameter_mm,
                       "feature_count":s.feature_count,"cutting_xy_mm":s.cutting_xy_mm,
                       "paths":paths,"features":features})
    data = {"schema_version":1,"format":"offline-cam-geometry","units":"mm",
            "manufacturing_ready":False,"project":project.name,"side":side,
            "coordinate_system":"canonical board XY, unmirrored",
            "stock_bounds":[x0,y0,x1,y1],"stock_assumed":True,
            "settings":{"effective_isolation_diameter_mm":diameter,"target_width_mm":target,
                        "passes":passes,"overlap":overlap,"cutout_diameter_mm":cutter,
                        "stock_margin_mm":stock_margin,"tab_anchors":tab_anchors,"tab_width_mm":tab_width},
            "stages":stages,"tab_gaps":job.cutout.tab_gaps,
            "isolation_residual_mm2":job.isolation.residual_mm2,
            "diagnostics":[{"code":d.code,"detail":d.detail} for d in job.diagnostics]}

    return data, job


def geometry_job(project, **settings):
    return plan_geometry_job(project, **settings)[0]


def assumed_stock(outline,stock_margin):
    """Shared nominal rectangular stock model for preview and tab editor."""
    if outline is None or not isfinite(stock_margin) or stock_margin<=0:
        raise ValueError("Outline and positive modeled stock margin required")
    xs,ys=zip(*outline.exterior)
    x0,y0,x1,y1=min(xs)-stock_margin,min(ys)-stock_margin,max(xs)+stock_margin,max(ys)+stock_margin
    return BoardOutline("assumed rectangular stock",((x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)))
