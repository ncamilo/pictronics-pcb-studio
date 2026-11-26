# RES-008 — Curved board outlines and internal cutouts

Status: submitted for CI. Builds on PR #2, commit 97f40eadce9a6981c232d5c6922384b78b8d54a7, whose two workflows passed.

The board outline domain now retains internal rings. The adapter constructs centerline loops from dark straight and circular Gerber strokes, merges exact endpoints, and classifies one outer boundary and disjoint strictly internal cutouts independent of file order and winding. Reject open, invalid, disjoint, touching, intersecting or nested loops; no automatic snapping or healing. Arc tessellation uses the previous preview parameters. The implementation supports one connected board only, not panelized islands or nested material islands. No CAM offset or tool diameter compensation is performed.

Tests: semicircular board, round cutout, two rectangular cutouts in noncanonical order, disjoint/touching/crossing outlines, nested/overlapping cutouts, and domain ring validation. Analytic areas and bounds. No GUI changes. Manufacturing remains disabled. Direct FlatCAM comparison, aperture macros, curved copper regions, and real KiCad board validation are still pending.
