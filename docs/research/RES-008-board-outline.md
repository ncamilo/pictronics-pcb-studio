# RES-008 — Curved board outlines and internal cutouts

Status: outline tests passed in CI. Builds on PR #2, commit 97f40eadce9a6981c232d5c6922384b78b8d54a7, whose two workflows passed.

The board outline domain now retains internal rings. The adapter constructs centerline loops from dark straight and circular Gerber strokes, merges exact endpoints, and classifies one outer boundary and disjoint strictly internal cutouts independent of file order and winding. Reject open, invalid, disjoint, touching, intersecting or nested loops; no automatic snapping or healing. Arc tessellation uses the previous preview parameters. The implementation supports one connected board only, not panelized islands or nested material islands. No CAM offset or tool diameter compensation is performed.

Tests: semicircular board, round cutout, two rectangular cutouts in noncanonical order, disjoint/touching/crossing outlines, nested/overlapping cutouts, and domain ring validation. Analytic areas and bounds. No GUI changes. Manufacturing remains disabled. Direct FlatCAM comparison, aperture macros, curved copper regions, and real KiCad board validation are still pending.

## Verified evidence
Commit 44b13ba8ba854829a5fc8189eb7f960226d438fc: 50 research tests passed on each OS with no warnings, https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45865052033. Core all four jobs succeeded; inspected Ubuntu 3.12 log showed 35 passed, 6 skipped (optional tests), https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45865052107.

## Cross-check preparation
The next commit adds a comparison module for already normalized, valid, nonempty polygonal XY geometries in mm: area, directional and symmetric difference, component/hole counts, bounds delta, discrete boundary Hausdorff distance. It does not align or certify geometries or execute FlatCAM. Analytic tests show that equal areas or bounds do not prove equivalence. Next gate: independently execute pinned upstream parser and feed its outputs into this comparator; set case-specific tolerances from source precision and tessellation. Drill/slot comparison and empty geometry handling are separate pending tasks.
