# Phase 4 — Ausbau: DB-Migration, Modul-Löschung, Docs, ADR-018

**Komplexität:** mechanisch · **Status:** pending
**Voraussetzung:** Phasen 1–3 committet (kein Code liest die Spalten mehr).

## Kontext (vor Arbeitsbeginn lesen)

- `README.md` dieses Plans (Kontrakt: DB-Sektion — Lösch-Regel für unresolved Items)
- `backend/photofant/db/models.py` — `Asset.phash`, `Face.phash`, `ReviewItem.phash_distance`
- `backend/alembic/versions/` — jüngste Migration als Muster (SQLite ⇒ `batch_alter_table` für Spalten-Drops)
- `backend/pyproject.toml` — `imagehash`-Dependency
- `docs/decisions/006-phash-duplikaterkennung.md`, `007-duale-duplikaterkennung-clip.md` — werden superseded/ergänzt
- `docs/models.md`, `docs/routes.md`, `docs/code-map.md`, `docs/glossary.md`

## AK

1. Alembic-Migration: löscht unresolved `dupe_candidate`-Rows mit `clip_distance IS NULL`, droppt danach die drei phash-Spalten; `alembic upgrade head` läuft auf einer Bestands-DB fehlerfrei.
2. `media/phash.py` gelöscht, `imagehash` aus `pyproject.toml` + Lockfile; `grep -ri phash backend/photofant/` → 0 Treffer.
3. ADR-018 angelegt; ADR-006 und ADR-007 tragen einen Superseded-/Ergänzt-Hinweis im Kopf.
4. `docs/models.md`, `routes.md`, `code-map.md`, `glossary.md` synchron; ruff + Tests + Frontend-Build grün.

## Checkliste

- [ ] **Alembic-Migration** (eine Datei, zwei Schritte in dieser Reihenfolge):
  1. `DELETE FROM review_item WHERE type='dupe_candidate' AND resolved_at IS NULL AND clip_distance IS NULL`
  2. `batch_alter_table`-Drops: `asset.phash`, `face.phash`, `review_item.phash_distance`.
  Downgrade: Spalten nullable wieder anlegen (Daten sind nicht wiederherstellbar — im Docstring vermerken).
- [ ] **`db/models.py`:** die drei Spalten-Definitionen entfernen.
- [ ] **`media/phash.py` löschen**; letzter Grep-Sweep `grep -ri "phash\|imagehash" backend/photofant/ frontend/src/` → 0 Treffer (Alembic-Historie ausgenommen).
- [ ] **`pyproject.toml`:** `imagehash>=4.3` raus; `uv lock` (bzw. `uv sync`) ausführen.
- [ ] **ADR-018** `docs/decisions/018-clip-only-duplikaterkennung.md` (~10 Zeilen): Kontext (pHash-Trefferqualität schlecht, vier Trägerfunktionen inventarisiert), Optionen (behalten als Import-Tripwire vs. komplett ersetzen), Entscheidung (CLIP-only; Import-Check wandert hinter den Embedding-Job; Face-Dedupe auf buffalo_l-Cosine), Konsequenzen (kein modellfreier Dupe-Pfad mehr; Kandidaten-Latenz = Embedding-Job; drei neue Settings-Keys). Supersedes ADR-006.
- [ ] **ADR-006/007:** Kopfzeile ergänzen: „**Superseded by ADR-018**" (006) bzw. „**Ergänzt durch ADR-018** — pHash-Zweig entfernt" (007).
- [ ] **Docs:** `models.md` (drei Spalten raus), `routes.md` (Restabgleich duplicates/classify/collections), `code-map.md` (Review-Queue-Zeile: `media/phash.py` raus; Suche-Zeile prüfen), `glossary.md` (pHash-Eintrag: entfernt/historisch markieren oder streichen).
- [ ] **CI-Gate:** `cd backend && uv run ruff check .` + `uv run pytest` · `cd frontend && npm run lint && npm run build`.

## Report-Back
