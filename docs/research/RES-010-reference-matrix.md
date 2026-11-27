# RES-010 — Expanded independent parser comparison

Status: original four reference fixtures passed on Ubuntu. Extended transparency cases pending.

Retain the original synthetic board, and add three authored, non-production fixtures: ordered dark/clear/re-dark rectangles (68 mm², 2 copper components and one hole), parameterized circular annulus (3π mm²), quarter-circle stroke (2π + 0.04π mm²). Include two drill diameters and a routed slot. Each new fixture has an independent analytic JSON oracle for both parsers; the comparator reports metrics before checking thresholds. Slot endpoint order is normalized only for geometry comparisons, not toolpath execution. Each fixture runs in the isolated upstream environment pinned to c948622f6b906f9910990d7bafbfb3012be21350, then in the existing Gerbonara environment. No changes to UI, CAM or manufacturing readiness.

Rectangular tolerance 1e-5 mm² and 1e-6 mm coordinate/boundary; curved fixture area tolerance 0.05 mm², cross-parser symmetric difference 0.08 mm² and discrete Hausdorff 0.02 mm, bounds 0.01 mm. These are provisional experimental limits, not machining accuracy. Do not loosen thresholds to hide discrepancies. If a case fails, investigate source semantics and approximation independently. The test set remains synthetic and does not include full real KiCad files, outlines in the reference comparison, negative macro flashes, thermal macros or complex regions.

## Verified matrix (commit 5ced1c3dab074ed1a899180a72736cc67d2d7ecf)
Reference run: https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45868602360. All four upstream exports and all comparisons passed with existing thresholds. CI and research also passed (65 research tests per OS; inspected core job 35 passed and 7 optional skips).

| Fixture | Studio area mm2 | FlatCAM area mm2 | Symmetric difference mm2 | Discrete boundary Hausdorff mm | Components | Holes |
|---|---:|---:|---:|---:|---:|---:|
| synthetic_board | 31.19242250775611 | 31.173432693868047 | 0.01898981388806478 | 0.0018068156922449424 | 1 | 0 |
| macro-ring | 9.423831752798312 | 9.412820216747082 | 0.01840299581681915 | 0.0019035568362852004 | 1 | 1 |
| ordered-polarity | 68.0 | 68.00000240000007 | 0.000007200000098350756 | 0.00000010000000116860974 | 2 | 1 |
| quarter-arc | 6.408624346638031 | 6.407002920018999 | 0.025728765404736505 | 0.001875666615075352 | 1 | 0 |

Analytical area, bounds, topology counts and drill/slot records passed for the three new cases in both parsers. Four synthetic fixtures are not evidence of general Gerber compliance or production readiness. Boundary Hausdorff is the discrete metric, not certified continuous error. No threshold changed.

## Additional acceptance checks
Add positive and negative parameterized ring flashes over pre-existing copper. The transparent center must preserve existing material in both polarities. Independent expected areas and topology are fixed before execution. The reference workflow now also runs for relevant source/dependency changes in PRs and on main, rather than being tied to feature/arc-preview only. No production code or machine commands modified.
