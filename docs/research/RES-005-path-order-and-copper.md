# RES-005 — Path ordering and copper composition

Status: experimental code submitted for CI, not production-ready.

The unmodified FlatCAM PathOrder module is isolated in vendor/flatcam with MIT license and exact blob provenance. NumPy 2.2.6 and Shapely 2.1.2 are installed only by the research workflow (Python 3.12). Production adoption requires transitive license and packaging review.

The independent adapter validates finite XY data, verifies multiplicity, and refuses directional paths unless reversal is explicitly permitted. Drill optimization is restricted to a single tool/operation group; no automatic reordering of manufacturing stages. Tests cover grid travel, 2-opt improvement, deterministic output, duplicates, invalid coordinates, geometry identity and reversal, and 1000 synthetic holes. Timing is observational, not a performance gate; rapid travel excludes cutting, Z lifts, acceleration and return.

Copper composition applies ordered union/difference to normalized polygonal shapes. A limited Gerbonara integration fixture uses bounds only because its known apertures are solid axis-aligned rectangles. General aperture conversion, arc tessellation, macros, image polarity and outline validation are still missing. No G-code or hardware commands. FlatCAM parser comparison remains pending.
