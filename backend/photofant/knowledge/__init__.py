"""Knowledge Engine — generische, domänen-agnostische Wissensbasis.

Markdown ist die einzige Quelle der Wahrheit (`knowledge/<type-plural>/<slug>.md`),
SQLite ist ein jederzeit neu aufbaubarer Cache (ab Phase 2). Die Engine kennt keine
KI, keine konkreten Typen wie „Film" — nur Entity + Type + Relationship; die Typen
kommen aus einer Domäne (`domains/<domain>.yaml`).
"""
