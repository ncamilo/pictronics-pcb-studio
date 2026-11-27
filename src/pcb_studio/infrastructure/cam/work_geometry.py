"""Version 2 CAM exchange in the same work frame as NC export."""
from dataclasses import asdict


def work_geometry(data,frame):
    # Do not modify canonical settings or geometry stored in the project.
    return {**data,"schema_version":2,"coordinate_system":"work XY",
            "work_frame":asdict(frame),
            "stock_bounds":frame.bounds(data["stock_bounds"]),
            "settings":{**data["settings"],
                        "tab_anchors":[frame.to_work(xy) for xy in data["settings"]["tab_anchors"]]},
            "stages":[{**s,"paths":[[frame.to_work(xy) for xy in path] for path in s["paths"]]}
                      for s in data["stages"]],
            "tab_gaps":[[frame.to_work(xy) for xy in path] for path in data["tab_gaps"]]}
