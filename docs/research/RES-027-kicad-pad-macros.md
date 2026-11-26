# RES-027 — KiCad pad macro compatibility

Reported by user on PWM 555 V2: unsupported aperture macro primitive. Exact input unavailable. Extend reviewed macro set to VectorLine (20) and CenterLine (21), required by KiCad RoundRect and RotRect. Verify rotated/off-center/diagonal shapes against independent analytic geometry and rounded pad oracle; maintain rejection of thermal and moire. Report filename, flash position, macro name and unsupported types. No physical machining or main changes. Validation pending CI and actual user file.
