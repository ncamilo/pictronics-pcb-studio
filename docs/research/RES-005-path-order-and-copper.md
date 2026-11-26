# RES-005 — Path ordering and copper composition

Status: initial experimental tests passed, not production-ready.

The unmodified FlatCAM PathOrder module is isolated in vendor/flatcam with MIT license and exact blob provenance. NumPy 2.2.6 and Shapely 2.1.2 are installed only by the research workflow (Python 3.12). Production adoption requires transitive license and packaging review.

The independent adapter validates finite XY data, verifies multiplicity, and refuses directional paths unless reversal is explicitly permitted. Drill optimization is restricted to a single tool/operation group; no automatic reordering of manufacturing stages. Tests cover grid travel, 2-opt improvement, deterministic output, duplicates, invalid coordinates, geometry identity and reversal, and 1000 synthetic holes. Timing is observational, not a performance gate; rapid travel excludes cutting, Z lifts, acceleration and return.

Copper composition applies ordered union/difference to normalized polygonal shapes. A limited Gerbonara integration fixture uses bounds only because its known apertures are solid axis-aligned rectangles. General aperture conversion, arc tessellation, macros, image polarity and outline validation are still missing. No G-code or hardware commands. FlatCAM parser comparison remains pending.

## Results (commit da82e5951a7ad6e56ade3b91387b590019b6d1f7)
Core CI: all four jobs passed, https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45840029942.
Research: 24 passed on each OS, https://github.com/ncamilo/pictronics-pcb-studio/actions/runs/45840017446.
64 shuffled grid holes: 2790.658 to 638.284 mm (77.13% reduction). 1000 seeded random holes: 89806.598 to 4354.347 mm, 0.0336 s Windows and 0.0610 s Ubuntu. Both OS produced the same distances. Baseline is shuffled input, not an optimized commercial CAM or machining time. One warning remained for G90 placement in the older Excellon test fixture; corrected in the following commit, alongside consistent LengthUnit use. Recheck CI. Vendored PathOrder blob verified identical to upstream.
