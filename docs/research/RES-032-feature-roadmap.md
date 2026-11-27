# RES-032 — Upstream feature study and prioritized integration roadmap

## Baseline and scope

Baseline 2f93ed8e5e34dff0f89297134a70e28a9d5e4f14 passed CI, Parser research, FlatCAM reference and Desktop preview (https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45913205276). User verified real PWM 555 V2 import and all three NC previews opened in bCNC 1.0.0; isolation simulation was visually plausible. Later simulations in that session had an unresolved issue. Physical machining has not been validated. This review is not a parity certification.

Reference snapshots inspected:
- [FlatCAM Evo c948622](https://github.com/MariusAdrian88/FlatCAM_Evo/tree/c948622f6b906f9910990d7bafbfb3012be21350), same pinned source used by reference CI.
- [bCNC 24540c5](https://github.com/vlachoudis/bCNC/tree/24540c5cc4c666962327a4966f7f3c8825def7e6), upstream master snapshot, not established to match the installed 1.0.0 build.
- [GRBL host interface](https://github.com/gnea/grbl/blob/master/doc/markdown/interface.md), [commands](https://github.com/gnea/grbl/blob/master/doc/markdown/commands.md). Actual Masuter firmware remains to be identified.

## Feature-to-source matrix

| Capability | Reference implementation inspected | Studio baseline | Proposed implementation / acceptance |
|---|---|---|---|
| Origin and reflection | FlatCAM DblSidedGen.py alignment_drills; bCNC GCode.py Orient, Sender.py _wcsSet; GRBL coordinate systems | Explicit offline XY frame, source axes shown | Separate board, work, machine and physical registration frames; reflected preview; preserve source coordinates; verify same transform across stages |
| Double-side registration | DblSidedGen.py bounds_drills, drills_fit_after_flip, alignment_matrices; AlignGen.py solve_rigid, residuals, snap, bounded_align | Reflection only | Independent flip line and work origin; generate symmetric/keyed registration holes, check stock, fixture and swept areas; one drill/registration plan; rigid fit with residuals and ambiguity rejection; no arbitrary scaling |
| Tabs and internal slug | CutOutGen.py _manual_gap_geometry, _cutout_anchor_points, _cutout_intervals, mouse_bite_holes | Straight full-depth tabs, manual coordinate entry; internal slug warning | Mouse snap to eligible contour; preview width plus cutter compensation; auto presets, edit/remove; reject corner/overlap; thin tabs and mouse bites later |
| Project model | FlatCAM object workflow; existing Studio PCBProject, JobPreview | Separate import, geometry, NC exports; no persistence | Versioned project settings, relative source paths and hashes, stable IDs, invalidation of derived data, save/load and roundtrip; no automatic resume |
| Tool and process library | FlatCAM tool database; MillingGen.py milling_drills_geometry/milling_slots_geometry | Nominal tool model, JSON, virtual NC tools | UI physical tools, materials, per-operation recipes; verify diameter/depth/stepdown, cutting length and plunge suitability; no invented machine settings |
| Isolation / DFM | FlatCAM isolation generator and existing reference tests | Multi-tool engine, UI single diameter, residual report | Expose rest machining, critical gap probes, minimum clearance and residual maps; compare swept geometry and preserve diagnostics |
| NC clearing / pockets | NccGen.py compute_area_to_clear, clear_polygon_worker; MillingGen.py | Not implemented | Bounded pocket clearing, exclusion regions, keep copper protected, residual coverage and topology checks |
| Drill milling / slots | MillingGen.py milling_drills_geometry, milling_slots_geometry; drilling research | Nominal matching tools, slot paths | Diameter-aware milling, peck/spot drill, hole geometry checks, no silent tool substitution |
| Path optimization | Existing vendored FlatCAM PathOrder; bCNC arcfit.py mergeLines/arcFit | Drill ordering, limited rest selection; line-only output | First lossless collinear merge; then bounded simplification and G2/G3 fitting; separate stages and tabs; verify swept copper clearance, error bounds, feed and direction; measure actual PWM file size and render latency |
| G-code interpreter and postprocessing | bCNC CNC.py motionStart/motionPath/motionEnd; FlatCAM GRBL_11_no_M6.py | Restricted offline G0/G1 readback and per-stage previews | Explicit modal state, G2/G3, I/J, planes, units, absolute/incremental, safe start/end and controller dialect; reject unsupported commands; independent roundtrip |
| Simulation | bCNC canvas and user-observed viewer; Studio native XY/XZ | Centerlines and event navigation | Source/work overlay, 3D tool-tip trajectory; bounded raster heightfield for actual removal later, distinguish cut and rapid, stage selection/reset, compare material and tabs |
| Machine profile and transport | bCNC Sender.py serialIO and GRBL1.py; vendor FlatCAM protocol; GRBL spec | Simulated machine service | Identify actual firmware, serial transport fake first, read-only status, MPos/WPos/WCO; explicit actions for homing/jog/WCS; alarm/disconnect block motion |
| Streaming | bCNC Sender.py serialIO, RX_BUFFER_SIZE=128; GRBL host interface | Not implemented | Fake serial send/response first; then character counting by bytes, FIFO ACK tracking, real-time controls, queue drain vs Idle; alarm/error/reset/reconnect test; never auto-resume |
| Auto-level | bCNC GCode.py Probe.scan/add/setZero/interpolate/splitLine; ProbePage.py; FlatCAM LevellingGen.py generate_probing_gcode | Empty probing infrastructure | Rectangular grid offline, complete measured grid + provenance, relative Z surface, bilinear interpolation, cell splitting and adaptive chord error; reject extrapolation, stale maps, missing/duplicate samples; preserve safe rapids; actual probing only after transport safety gate |
| Tool length / change | bCNC CNC.py toolChange, ProbePage.py ToolFrame; FlatCAM GRBL_11_no_M6.py | No physical tool change | Explicit stage stops, operator acknowledgement, validated tool length and safe retract; invalidate Z/map references as needed |
| Production extensions | FlatCAM Panelize/RulesCheck/Paint; bCNC plugins | Not implemented | Panelization, fiducials, copper thieving, stencil/marking, job report and batch processing after core workflow |

## Important implementation observations

- FlatCAM's axis names describe the mirror line (X line reverses Y), whereas Studio mirror X reverses X. Label flip direction explicitly to avoid ambiguity.
- FlatCAM bounds_drills implements a keyed third hole and a geometric fit-after-flip check. A generic reflected layer is not sufficient for physical registration.
- FlatCAM manual gaps project a point onto a selected contour and use gap length equal to desired bridge width plus cutter diameter. Existing Studio tab generator already models this length; add UI rather than rewrite it.
- bCNC Probe uses a serpentine grid and bilinear interpolation; its interpolation can extrapolate beyond grid edges. Studio should reject out-of-coverage cutting, and bound interpolation error within a cell.
- bCNC Orient estimates rotation and translation from point pairs and reports residuals. Use an independently implemented rigid fit and require additional check points for validation.
- bCNC arcfit plugin calls mergeLines then arcFit. Do not assume visual similarity or Hausdorff alone proves copper clearance. Compare swept areas and retain protected material.
- A GRBL ok response is not proof motion finished. Machine state and queue completion must both be considered. No EEPROM settings in ordinary program streaming.
- Source references are behavioral research, not permission to copy; existing vendor provenance remains separate. No new third-party code copied. Audit individual licenses before reuse.

## Proposed release gates

1. **Project preparation:** graphical tabs, stable project persistence, work frame preview, independent flip-axis registration. Verify geometry and project roundtrip using synthetic tests plus private PWM files locally.
2. **CAM quality:** physical tool/recipe UI, residual overlays, multi-tool isolation, clearance/exclusion checks, hole/slot milling; optimize segments conservatively. Establish benchmarks for the real 22,207-line isolation path and 8 MB file. No fixed speedup claim.
3. **Offline CNC:** modal reader/postprocessor, explicit machine profile, 3D preview and preflight. Independent checks of bounds, Z, feed, fixture geometry, swept material and NC roundtrip.
4. **Controller integration:** identify hardware/firmware, fake serial, read-only telemetry, explicit homing/jog/work-zero, transport failure and abort tests. No real motion before an explicit operator-controlled test plan.
5. **Probing and execution:** offline height compensation first, validated probe device and map, tool-change handling, check-mode where supported, controlled dry run and supervised physical test with appropriate safety precautions.
6. **First production candidate:** PWM 555 V2 fabricated and electrically checked, two-side registration measured, release reproducible. Add larger production features only after baseline qualification.

Next concrete increment: graphical tabs using current cutout engine; then project save/load and physical flip-line registration before optimizing/exporting manufacturing programs. Documentation-only change; no production logic or original PWM files added.
