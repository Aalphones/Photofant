# FINDINGS — P6 Suche & Alben

> Erkenntnisse während der Umsetzung, getaggt auf die Phase, die sie betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>`

- [x] → Phase 2: **FTS5 vs LIKE für Caption-Suche** — Bei erwartetem Bestand (Hunderte bis wenige Tausend Fotos mit kurzen Captions) ist `LIKE '%q%'` auf der SQLite-Caption-Spalte ausreichend schnell (< 5 ms, kein Full-Table-Scan nötig bei Index auf `asset.id`). FTS5 würde eine zusätzliche virtuelle Tabelle, eine Alembic-Migration und einen Sync-Trigger erfordern — Kosten/Nutzen klar negativ. Entscheidung: LIKE in Phase 2, FTS5 frühestens bei > 50 000 Assets evaluieren.
