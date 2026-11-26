# RES-009 — Local aperture composition

Status: submitted for CI. Previous comparator commit b76b5733e450d221e603f37c0a366ad552f973a9 passed both CI workflows.

Separate aperture exposure from layer polarity. Build each flash as a positive stamp using aperture.flash(x, y, MM, True), compose its primitives locally, then add/subtract the resulting geometry according to the original object's layer polarity. This preserves earlier copper underneath transparent aperture holes. Standard circular, rectangular and obround aperture holes and restricted macros with circle and straight outline primitives are supported for preview. Macro expressions are evaluated by Gerbonara, not by our own parser. Reject other macro primitive types (including thermal, moire, vector/center line) pending dedicated validation. No generic macro coverage claimed.

Analytic tests include parameterized annulus, standard annulus, dark/clear ring over existing copper, disjoint circular macro and triangular macro; thermal is explicitly rejected. No CNC changes. Preview resolution unchanged. Source inspected: https://github.com/jaseg/gerbonara (apertures.py, graphic_objects.py, aperture_macros/parse.py and primitive.py); runtime remains pinned to 1.6.3. Direct FlatCAM parser comparison remains pending.
