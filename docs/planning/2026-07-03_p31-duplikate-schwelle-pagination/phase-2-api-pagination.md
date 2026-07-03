# Phase 2 — Backend: Pagination + Query-Fix

## Kontext (vor Umsetzung lesen)

- `README.md` dieses Plans — Kontrakt-Sektion (Response-Shape, Sortierung)
- `backend/photofant/api/review.py` — `list_dupe_pairs` (heute: alle Paare, 2 COUNT-Queries
  pro Paar in Python, Auto-Resolve pro Zeile)
- `backend/photofant/db/models.py` — `ReviewItem`, `Asset`, `AssetInstance`
- `docs/routes.md` — Eintrag zu `GET /review/dupes`
- Konvention: `docs/conventions/python.md`

**Chesterton:** Der heutige Python-Loop existiert, um Papierkorb-Paare beim Listen
auto-aufzulösen (Papierkorb-Move erzeugt sonst Geister-Paare). Diese Funktion bleibt —
sie wandert nur in ein Bulk-UPDATE vor dem SELECT.

## Abnahmekriterien

1. `GET /api/review/dupes?offset&limit` liefert `{ items, total }` gemäß Kontrakt;
   `limit` default 50, hart gedeckelt auf 200; Sortierung wie im Kontrakt.
2. Auto-Resolve (Papierkorb): ein Bulk-UPDATE (`resolution = "auto_trashed"`) für alle
   ungelösten Paare, deren Asset A **oder** B keine aktive Instanz mehr hat — vor Count+Select,
   Verhalten identisch zu heute.
3. Konstante Query-Anzahl pro Request (UPDATE + COUNT + Seiten-SELECT mit beiden Assets
   gejoint) — keine Schleifen-Queries mehr.
4. Fehlende `asset_b`-Referenzen (heute: warn + skip) brechen die Seite nicht.
5. `ruff check` grün; bestehende Backend-Tests grün.

## Checkliste

- [ ] `api/review.py`: Response-Model `DupePageDto { items: list[DupePairDto], total: int }`
- [ ] Bulk-Auto-Resolve als ein UPDATE mit Subquery auf `AssetInstance.deleted_at IS NULL`
- [ ] Seiten-Query: `ReviewItem` + Asset A + Asset B über Aliase in einem SELECT,
      `ORDER BY (phash_distance IS NULL), phash_distance, clip_distance, id`,
      `offset/limit`, separater `COUNT(*)` für `total`
- [ ] Doc-Update: `docs/routes.md` — Query-Params + neue Response-Shape
- [ ] `uv run ruff check .` + Backend-Tests

## Report-Back
