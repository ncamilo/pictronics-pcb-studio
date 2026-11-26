# RES-007 — Circular copper strokes and import error boundary

Status: initial arc preview tests passed on both operating systems. Main remains unchanged. PR #1 was merged at 1b61e91111bee5b1b7d8bc6800e94f1b404be2e5; both CI workflows passed. Copilot review identified that malformed polygon conversion could escape as a raw ValueError. Copper conversion and composition now share an exception boundary, with a regression fixture.

Circular-aperture copper strokes now support clockwise, counterclockwise and full-circle arcs via Gerbonara primitives (absolute centers in mm). Chord sagitta target 0.001 mm, separate radius consistency tolerance 0.00001 mm, segment cap 100000; these are preview parameters, not validated machining tolerances. Existing fixed buffer resolution is retained. The new tests compare analytic area, bounds and full-circle hole topology. Curved regions, arc outlines, aperture macros and complex polarity remain unsupported. The project cannot authorize manufacture.

Next: expand format coverage, compare identical fixtures against the pinned FlatCAM parser using geometric differences rather than bounding boxes alone. No direct FlatCAM parser execution in this commit. UI unchanged.

## Verified results
Commit 5dab7732d5874ad11b9909eb24b7f8ba6157911e: all four core CI jobs passed (https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45864210805). Research: 42 tests passed on each OS, including 90-degree CCW, 270-degree CW, full circle and degenerate-region regression; no warnings in inspected logs (https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45864210781).

## FlatCAM cross-check plan
Pinned upstream revision c948622f6b906f9910990d7bafbfb3012be21350. Inspected tests/test_gerber_parser.py (get_gerber_parser, MockApp) and tests/test_excellon.py (parse, dump), plus tests/conftest.py. The parser test helpers depend on application defaults and Qt; conftest isolates user settings and argv. Use a separate process/environment for upstream, avoiding mixing PyQt6 and PySide6. Parse the same authorized fixtures in both environments; normalize mm and export copper polygon geometry as WKB and drills as explicit XY/diameter/slot records. Compare symmetric difference, topology, bounds and independently calculated expected geometry; no silent acceptance based on matching bounds. Record simplification, tessellation, dependency versions, and warnings. This is an implementation plan, not executed comparison.
