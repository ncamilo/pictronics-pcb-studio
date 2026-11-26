# RES-012 — Isolation coverage and candidate evaluation

Status: submitted for CI. Experimental only.

Define one explicit target band: buffer(copper, target_width) minus buffer(copper, clearance), intersect board material. Evaluate approximate swept disks along preview paths using nominal tool radius (not the inflated radius used for collision checks). Report target, covered and residual area, coverage fraction, residual WKB, merged passes and disappearing interior-ring counts. Preserve rejected tool candidates and reasons. Same target for all candidates; no automatic selection or execution.

Test analytic area partition, narrow gap point coverage, disappearing hole, additional passes, board edge rejection and invalid parameters. Narrower tools may reach gaps but cover less total area for equal pass count, so coverage fraction alone cannot select a tool. The ring counts do not prove topology equivalence. Coverage is approximate, not electrical isolation or physical machining validation. No Z, feeds, G-code or machine control. Next: compare isolation contours against pinned FlatCAM on common polygonal input, then evaluate realistic tool/clearance/tolerance choices and actual KiCad board. No external code copied.
