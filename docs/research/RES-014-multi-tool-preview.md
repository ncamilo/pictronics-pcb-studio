# RES-014 — Residual-aware multi-tool preview

Status: initial whole-ring multi-tool tests passed on Windows and Ubuntu.

The planner evaluates tools in the explicit supplied order against a common target band. Each candidate uses the existing validated isolation preview. Keep an entire closed ring if its nominal swept area contributes more than a configurable area threshold (default 0.00001 mm²) to the remaining target or reaches an explicitly supplied uncovered critical point. Record rejected tools, retained rings, new area, residual WKB and candidate/selected centerline lengths. Preserve pass order and ring direction. No source copied from FlatCAM in this step.

Independent fixtures: coarse/fine narrow gap, isolated internal cavity, duplicate tool (no new area), edge rejection and continuation, unresolved probe, probe override, direction and invalid settings. No automatic tool choice, no segment clipping, no automatic electrical net discovery, no feeds/Z/rapid motion/G-code. A high coverage percentage or covered point does not establish electrical isolation. Tiny residual components and approximation error require additional validation. Compare future segment-level rest machining against this conservative whole-ring baseline. Manufacturing readiness is always false. The interface and main remain unchanged.

## Verified results
Commit 46a6ca37366a6f10ec5841f61f41da77da30fa53: 108 research tests passed on each OS (14 new tests); CI passed. https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45885513736
Narrow gap: target 10.837688528 mm2; coarse residual 0.777663912 mm2; final residual 0.000000000 mm2 at displayed precision. Coarse/fine lengths 25.287630438 and 32.567586251 mm. Critical probe covered.
Cavity: fine tool candidate centerline length 40.667793125 mm; selected centerline 0.184000000 mm (99.55% reduction for fine stage only); residual 0.004830315 mm2. Both platforms printed identical metrics. These are synthetic nominal planar results, not machining time or electrical isolation evidence. FlatCAM reference rerun for the multi-tool commit was still in progress when inspected; it tests single-tool offset equivalence, not FlatCAM rest machining. No GUI, machine or main changes.
