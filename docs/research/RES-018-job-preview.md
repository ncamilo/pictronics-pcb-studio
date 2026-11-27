# RES-018 — Integrated CAM job preview

Status: submitted for CI.

All three workflows at c6dc940b0b7a07e99b7bde95094a855873d5332f completed successfully, including five cutout comparisons (https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45889530596).

Compose the existing engines in the CAM infrastructure adapter, keeping application/domain free of Shapely. Explicit one-sided PCB project, outline, stock, isolation tools, target width, cutout diameter and optional tabs. Validate geometry atomically; output immutable subplans and ordered stage references: isolation (supplied tool order, selected rings only), drill groups, slot groups, internal cutouts, exterior cutout. Preserve source indices and original side/coordinates; no mirroring, physical tool assignment, motion or executable G-code. Cutting XY length excludes drill Z, rapids, changes and depth passes. Diagnostics include rejected tools, no isolation paths, residual area above explicit reporting threshold (default 1e-6 mm²; not acceptance tolerance), unresolved critical probes, missing drill features, duplicate pairs, internal slug retention and absent exterior tabs. Diagnostics are not a complete manufacturing checklist; manufacturing readiness is always false. Invalid geometry raises instead of returning partial results. No GUI or machine changes.

Tests cover integrated ordering, references, redundancy, rejected isolation, residual probes, duplicates, no tabs/drills, bottom frame, invalid inputs and actual synthetic Gerber/Excellon import. Real KiCad files, full rest machining comparison, two-sided setup, tool library, cross-operation overlap checks, stock/clamp/slug strategy, Z and simulation remain pending. No new upstream source copied.
