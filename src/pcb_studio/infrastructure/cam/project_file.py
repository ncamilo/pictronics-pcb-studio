"""Versioned portable project file with embedded source bytes."""
import base64
from dataclasses import asdict, replace
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from pcb_studio.application.import_project import import_project
from pcb_studio.domain.work_frame import WorkFrame
from pcb_studio.domain.pcb import PanelOutline
from pcb_studio.domain.depth import DepthSetup, validate_depth
from pcb_studio.domain.tools import ProcessSettings
from pcb_studio.infrastructure.cam.gerbonara_adapter import GerbonaraImporter
from pcb_studio.infrastructure.cam.geometry_job import plan_geometry_job

MAX_FILE=32*1024*1024
MAX_PROJECT=128*1024*1024


def capture_sources(top="",bottom="",outline="",drills=()):
    roles=[(role,path) for role,path in (("top",top),("bottom",bottom),("outline",outline)) if path]
    roles.extend(("drill",path) for path in drills)
    if len({Path(path).resolve() for _,path in roles})!=len(roles):
        raise ValueError("A file cannot be assigned more than once")
    sources=[]
    total=0
    for role,path in roles:
        p=Path(path)
        if p.stat().st_size>MAX_FILE:
            raise ValueError("Source file too large")
        data=p.read_bytes()
        total+=len(data)
        if len(data)>MAX_FILE or total>MAX_PROJECT//2:
            raise ValueError("Embedded sources exceed project budget")
        sources.append({"role":role,"name":p.name,"sha256":sha256(data).hexdigest(),
                        "base64":base64.b64encode(data).decode("ascii")})
    return sources


def import_sources(name,sources):
    if not isinstance(name,str) or not name.strip() or not isinstance(sources,list):
        raise ValueError("Invalid project source metadata")
    if len(sources)>128:
        raise ValueError("Too many source files")
    total=0
    roles=[]
    with tempfile.TemporaryDirectory(prefix="pcb-project-") as directory:
        copper,drills,outline=[],[],None
        labels={}
        for i,item in enumerate(sources):
            role=item["role"]
            label=item["name"]
            if (role not in ("top","bottom","outline","drill") or not isinstance(label,str)
                    or not label or len(label)>512 or "/" in label or chr(92) in label):
                raise ValueError("Invalid embedded source role or name")
            if role!="drill" and role in roles:
                raise ValueError("Duplicate source role")
            roles.append(role)
            encoded=item["base64"]
            if not isinstance(encoded,str) or len(encoded)>4*((MAX_FILE+2)//3):
                raise ValueError("Invalid embedded source size")
            data=base64.b64decode(encoded,validate=True)
            total+=len(data)
            if len(data)>MAX_FILE or total>MAX_PROJECT//2 or sha256(data).hexdigest()!=item["sha256"]:
                raise ValueError("Source checksum or size mismatch")
            suffix=".drl" if role=="drill" else ".gbr"
            path=Path(directory)/f"{i:03d}{suffix}"
            path.write_bytes(data)
            labels[str(path)]=label
            if role in ("top","bottom"):
                copper.append((path,role))
            elif role=="drill":
                drills.append(path)
            else:
                outline=path
        project=import_project(GerbonaraImporter(allow_panel=True),name,copper_files=tuple(copper),
                               drill_files=tuple(drills),outline_file=outline)
        profile=project.outline
        if isinstance(profile, PanelOutline):
            label=labels[profile.source]
            profile=replace(profile,source=label,boards=tuple(replace(b,source=label) for b in profile.boards))
        elif profile is not None:
            profile=replace(profile,source=labels[profile.source])
        return replace(project,
            copper=tuple(replace(layer,source=labels[layer.source]) for layer in project.copper),
            drills=tuple(replace(layer,source=labels[layer.source]) for layer in project.drills),
            outline=profile)


def cam_settings(data):
    if data is None:
        return None
    s=data["settings"]
    return dict(side=data["side"],diameter=s["effective_isolation_diameter_mm"],
                target=s["target_width_mm"],passes=s["passes"],overlap=s["overlap"],
                cutter=s["cutout_diameter_mm"],stock_margin=s["stock_margin_mm"],
                tab_anchors=tuple(tuple(xy) for xy in s["tab_anchors"]),tab_width=s["tab_width_mm"])


def save_project(path,project,sources,frame,cam,nc):
    path=Path(path)
    if not path.name.lower().endswith(".pcbstudio.json"):
        raise ValueError("Use .pcbstudio.json")
    if not sources:
        raise ValueError("No embedded source files")
    record={"format":"pictronics-pcb-studio","schema_version":1,
            "manufacturing_ready":False,"name":project.name,"sources":sources,
            "work_frame":asdict(frame),"cam":cam_settings(cam),
            "nc":None if nc is None else {"setup":asdict(nc[0]),
                         "settings":[asdict(p) for p in nc[1]]}}
    payload=json.dumps(record,allow_nan=False,indent=2).encode("utf-8")
    if len(payload)>MAX_PROJECT:
        raise ValueError("Project archive too large")
    fd,temp=tempfile.mkstemp(prefix=".pcb-save-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def load_project(path):
    path=Path(path)
    if path.stat().st_size>MAX_PROJECT:
        raise ValueError("Project archive too large")
    d=json.loads(path.read_text(encoding="utf-8"))
    if (d["format"]!="pictronics-pcb-studio" or type(d["schema_version"]) is not int
            or d["schema_version"]!=1 or d["manufacturing_ready"] is not False):
        raise ValueError("Unsupported project format/version")
    project=import_sources(d["name"],d["sources"])
    frame=WorkFrame(tuple(d["work_frame"]["origin"]),d["work_frame"]["mirror"])
    cam,job,nc=None,None,None
    if d["cam"] is not None:
        settings=dict(d["cam"])
        settings["tab_anchors"]=tuple(tuple(xy) for xy in settings["tab_anchors"])
        cam,job=plan_geometry_job(project,**settings)
    if d["nc"] is not None:
        setup=DepthSetup(**d["nc"]["setup"])
        params=tuple(ProcessSettings(**p) for p in d["nc"]["settings"])
        if job is None or len(params)!=len(job.stages):
            raise ValueError("NC settings do not match CAM stages")
        for s,p in zip(job.stages,params):
            validate_depth(s.operation,p.depth_mm,setup)
            if (p.feed_xy_mm_min is None)!=(s.operation=="drill"):
                raise ValueError("NC feed does not match operation")
        nc=(setup,params)
    return project,d["sources"],frame,cam,job,nc
