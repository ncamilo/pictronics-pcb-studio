# FlatCAM Evo provenance

Repository: https://github.com/MariusAdrian88/FlatCAM_Evo
Commit: c948622f6b906f9910990d7bafbfb3012be21350
File: appPlugins/Common/grbl/grbl_protocol.py
Git blob: a67f8054fb64880f17104d280aa6729f5d614d80
License: MIT; original file header and root LICENSE retained.
Changes: none to the imported source.
Scope: experimental pure parsing; not wired into the machine service. No serial writes or motion. Future adapter must reject unknown states, stale offsets, inconsistent/invalid reports and non-finite derived values before using them for any motion decision.
