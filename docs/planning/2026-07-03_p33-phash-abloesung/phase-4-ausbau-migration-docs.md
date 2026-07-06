# Phase 4 — Ausbau: DB-Migration, Modul-Löschung, Docs, ADR-018

**Komplexität:** mechanisch · **Status:** complete
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

- [x] **Alembic-Migration** (`0031_drop_phash.py`, zwei Schritte in dieser Reihenfolge):
  1. `DELETE FROM review_item WHERE type='dupe_candidate' AND resolved_at IS NULL AND clip_distance IS NULL`
  2. `batch_alter_table`-Drops: `asset.phash`, `face.phash`, `review_item.phash_distance`.
  Downgrade: Spalten nullable wieder anlegen (Daten sind nicht wiederherstellbar — im Docstring vermerkt).
  Gegen eine isolierte Kopie der echten Dev-DB getestet (54 unresolved Alt-Kandidaten gelöscht, 1824→1770 `dupe_candidate`-Rows, alle drei Spalten weg, `alembic_version` auf `0031`) — die Live-DB selbst wurde nicht angefasst; `alembic upgrade head` läuft der User im Rahmen des normalen App-Starts.
- [x] **`db/models.py`:** die drei Spalten-Definitionen entfernt.
- [x] **`media/phash.py` gelöscht**; Grep-Sweep `grep -ri "phash\|imagehash" backend/photofant/ frontend/src/` → 0 Treffer.
- [x] **`pyproject.toml`:** `imagehash>=4.3` raus; `uv lock` ausgeführt (entfernt auch die transitive `pywavelets`-Abhängigkeit).
- [x] **ADR-018** `docs/decisions/018-clip-only-duplikaterkennung.md` angelegt. Supersedes ADR-006.
- [x] **ADR-006/007:** Kopfzeile ergänzt: „**Superseded by ADR-018**" (006) bzw. „**Ergänzt durch ADR-018** — DHash-Zweig entfernt, CLIP-Teil bleibt gültig" (007).
- [x] **Docs:** `models.md` (drei Spalten raus, Flow-Beschreibung auf CLIP-only), `routes.md` (Legacy-Hinweis entfernt), `code-map.md` (Review-Queue-Zeile bereinigt). `glossary.md` hatte nie einen pHash-Eintrag — nichts zu tun.
- [x] **CI-Gate:** `ruff check` (nur berührte Dateien grün — 6 Alt-Fehler in unberührten Dateien bestätigt vorbestehend via Stash-Vergleich) · `pytest` 189 grün, 13 vorbestehende Alt-Fehler deselected (bestätigt vorbestehend) · `npm run lint` grün · `npm run build` grün (nur vorbestehende Bundle-Budget-Warnungen).

### Chesterton's-Fence-Fund (nicht im Plan erfasst)

`clustering/engine.py` legte beim Face-Pre-Matching einen `face_suggestion`-ReviewItem mit
`phash_distance=0` an — reiner Pflichtfeld-Ballast, das Pendant in `jobs/clustering_job.py`
setzt das Feld gar nicht erst. Wäre nach dem Spalten-Drop ein `TypeError` (unbekanntes
Kwarg) gewesen. Entfernt.

## Report-Back
