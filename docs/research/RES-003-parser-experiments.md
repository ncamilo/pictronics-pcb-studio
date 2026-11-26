# RES-003 — Parser experiments

Status: initial experiments implemented; CI results pending.

Gerbonara 1.6.3 (Apache-2.0; Python >=3.12 per https://pypi.org/project/gerbonara/1.6.3/) is an experimental dependency only. The core retains Python 3.11 support. The separate parser-research workflow installs the pinned candidate on Windows and Ubuntu with Python 3.12.

Initial synthetic tests in tests/test_parser_research.py:
- Metric circular flash: center (10,20) mm, diameter 2 mm.
- Imperial circular flash: center (1,2) inch, diameter 0.1 inch, bounds converted to mm.
- Excellon: two 0.8 mm drills at (10,20) and (15,25) mm.

These are object-count and bounding-box smoke tests, not complete geometric validation. The ordinary core suite skips them when Gerbonara is absent; the dedicated workflow explicitly installs and imports it before running the tests. No production parser adapter or CNC behavior is added.

Next gates: rectangular/obround apertures, stroke widths, arcs, ordered clear/dark composition, macros, outline closure, slots, invalid input, tessellation and symmetric difference. Compare against FlatCAM Evo at revision c948622f6b906f9910990d7bafbfb3012be21350 using equivalent fixtures and an independent geometric oracle. Assess whether the integration cost of extracting FlatCAM parsers is justified. Audit licenses and transitive dependencies before adoption. Record actual CI results separately.
