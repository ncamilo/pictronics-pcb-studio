# RES-010 — Expanded independent parser comparison

Status: submitted for CI; no results claimed yet.

Retain the original synthetic board, and add three authored, non-production fixtures: ordered dark/clear/re-dark rectangles (68 mm², 2 copper components and one hole), parameterized circular annulus (3π mm²), quarter-circle stroke (2π + 0.04π mm²). Include two drill diameters and a routed slot. Each new fixture has an independent analytic JSON oracle for both parsers; the comparator reports metrics before checking thresholds. Slot endpoint order is normalized only for geometry comparisons, not toolpath execution. Each fixture runs in the isolated upstream environment pinned to c948622f6b906f9910990d7bafbfb3012be21350, then in the existing Gerbonara environment. No changes to UI, CAM or manufacturing readiness.

Rectangular tolerance 1e-5 mm² and 1e-6 mm coordinate/boundary; curved fixture area tolerance 0.05 mm², cross-parser symmetric difference 0.08 mm² and discrete Hausdorff 0.02 mm, bounds 0.01 mm. These are provisional experimental limits, not machining accuracy. Do not loosen thresholds to hide discrepancies. If a case fails, investigate source semantics and approximation independently. The test set remains synthetic and does not include full real KiCad files, outlines in the reference comparison, negative macro flashes, thermal macros or complex regions.
