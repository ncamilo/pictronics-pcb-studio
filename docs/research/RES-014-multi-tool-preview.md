# RES-014 — Residual-aware multi-tool preview

Status: submitted for CI; results pending.

The planner evaluates tools in the explicit supplied order against a common target band. Each candidate uses the existing validated isolation preview. Keep an entire closed ring if its nominal swept area contributes more than a configurable area threshold (default 0.00001 mm²) to the remaining target or reaches an explicitly supplied uncovered critical point. Record rejected tools, retained rings, new area, residual WKB and candidate/selected centerline lengths. Preserve pass order and ring direction. No source copied from FlatCAM in this step.

Independent fixtures: coarse/fine narrow gap, isolated internal cavity, duplicate tool (no new area), edge rejection and continuation, unresolved probe, probe override, direction and invalid settings. No automatic tool choice, no segment clipping, no automatic electrical net discovery, no feeds/Z/rapid motion/G-code. A high coverage percentage or covered point does not establish electrical isolation. Tiny residual components and approximation error require additional validation. Compare future segment-level rest machining against this conservative whole-ring baseline. Manufacturing readiness is always false. The interface and main remain unchanged.
