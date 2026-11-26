# RES-007 — Circular copper strokes and import error boundary

Status: submitted for CI. Main remains unchanged. PR #1 was merged at 1b61e91111bee5b1b7d8bc6800e94f1b404be2e5; both CI workflows passed. Copilot review identified that malformed polygon conversion could escape as a raw ValueError. Copper conversion and composition now share an exception boundary, with a regression fixture.

Circular-aperture copper strokes now support clockwise, counterclockwise and full-circle arcs via Gerbonara primitives (absolute centers in mm). Chord sagitta target 0.001 mm, separate radius consistency tolerance 0.00001 mm, segment cap 100000; these are preview parameters, not validated machining tolerances. Existing fixed buffer resolution is retained. The new tests compare analytic area, bounds and full-circle hole topology. Curved regions, arc outlines, aperture macros and complex polarity remain unsupported. The project cannot authorize manufacture.

Next: expand format coverage, compare identical fixtures against the pinned FlatCAM parser using geometric differences rather than bounding boxes alone. No direct FlatCAM parser execution in this commit. UI unchanged.
