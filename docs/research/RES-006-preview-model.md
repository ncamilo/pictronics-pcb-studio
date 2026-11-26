# RES-006 — Canonical PCB preview model and import adapter

Status: experimental adapter and model passed initial CI. The parser choice remains provisional.
Domain uses standard Python tuples/dataclasses, canonical mm coordinates and explicit copper side; no Gerbonara/Shapely types cross the port. No implicit mirroring, offset or recentering. Source filenames retained; detailed source metadata and diagnostic model deferred. Geometry validity is checked by the adapter, not fully by the domain. PCBProject.manufacturing_ready is always False.

Supported preview subset: solid circular/rectangular/obround flashes, circular-aperture straight strokes, simple straight polygon regions, ordered polarity composition, round drill hits, straight routed slots, one simple closed outline of straight segments (centerline rather than copper width). Reject parser warnings and unsupported apertures, macros, holes in apertures, arcs, curved regions, multiple outline loops. This is not a full Gerber compliance or fail-safe manufacturing parser. Gerbonara may normalize input before adapter inspection; additional raw syntax/metadata validation is needed. Fixed 64 segments per quadrant for preview is not a certified machining tolerance.

Reference: https://gerbolyze.gitlab.io/gerbonara/api-concepts.html and https://github.com/jaseg/gerbonara (source inspection; runtime pin remains 1.6.3). No external code copied in this step. Tests use analytic geometry, unit conversion, outline closure and negative cases. A complete synthetic PCB fixture is added in the next commit. FlatCAM cross-check, arc/macro conversion and GUI preview remain future work.

## Verified initial results
Commit 0d3f1a56cebdc9ab3b606b1a312deac0eebbda48: research workflow 35 passed on both Windows and Ubuntu, no warnings (https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45841561542). Core workflow all four jobs passed; inspected Windows 3.12 log showed 30 passed and 5 optional modules skipped (https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45841573256). The next commit adds the import use case and a 30 x 20 mm synthetic board with alignment checks. Its CI is not yet recorded here.
