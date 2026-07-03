# Phase 1 — Datenmodell & Seed-Katalog

**Tier:** heikel (Schema-Entscheidung, Migration, Seed-Daten)

## Kontext (vor Start lesen)

- [`backend/photofant/db/models.py`](../../../backend/photofant/db/models.py) — bestehende Tabellen, Stil der Mapped-Columns. `ProcessingLedger.classified` existiert hier schon ungenutzt.
- [`backend/alembic/versions/0009_classified_flag.py`](../../../backend/alembic/versions/0009_classified_flag.py) — Vorlage für eine Migration.
  **Korrektur:** Zwischen Plan-Erstellung und Umsetzung sind Migrationen `0010`–`0028`
  dazugekommen (P19/P29 u.a.) — tatsächliche nächste Nummer ist **`0029`**,
  `down_revision = "0028"`.
- [`docs/models.md`](../../../docs/models.md) — Code-Referenz-Doc, wird in Phase 6 nachgezogen (hier nur die neuen Tabellen vormerken).
- Konzept-Katalog: [`KONZEPT.md`](KONZEPT.md), Abschnitte „Metadaten-Kategorien" + „Konfigurierbares CLIP".
- [`docs/conventions/python.md`](../../../docs/conventions/python.md)

## Akzeptanzkriterien

1. Drei neue Tabellen exakt nach Kontrakt (README): `classification_category`,
   `classification_label`, `asset_classification` — inkl. der genannten
   Indizes, FKs (`ON DELETE CASCADE` wo angegeben) und Unique-Constraints.
2. `ProcessingLedger.classified` wird **wiederverwendet** — keine neue Ledger-Spalte.
3. Migration `0010_classification.py` legt die Tabellen an und **seedet** den
   Konzept-Katalog (Kategorien mit `builtin=1`, ihre Labels). Migration ist
   reversibel (`downgrade` droppt die drei Tabellen).
4. Single-/Multi-Zuordnung der Seed-Kategorien folgt dem Konzept:
   `Medium`, `Realismus`, `Franchise`, `Charakter`, `Künstler`, `AI-Modell` → `single`;
   `Stil`, `Motiv`, `Szene`, `Eigenschaften`, `Technik` → `multi`.
5. Seed-Labels haben `clip_prompts = NULL` (Template greift) und sinnvolle
   `wd14_tags` dort, wo ein offensichtlicher WD14-Tag existiert (z.B. Label
   „Anime" → `["anime"]`, „Monochrome" → `["monochrome", "greyscale"]`). Wo
   kein klarer Tag existiert: `wd14_tags = NULL` (rein CLIP).
6. `ruff check` grün; ein Smoke-Test legt die DB neu an und prüft, dass die
   Seed-Kategorien + Labels vorhanden sind.

## Checkliste

- [x] `db/models.py`: `ClassificationCategory`, `ClassificationLabel`, `AssetClassification` ergänzen (Stil der bestehenden Modelle matchen).
- [x] `alembic/versions/0029_classification.py`: `create_table` ×3 + Indizes; `down_revision` auf `0028` gesetzt (Nummer korrigiert, s.o.).
- [x] Seed-Daten als Python-Konstante (`backend/photofant/classification/seed.py`) — Liste aus dem Konzept; in der Migration eingespielt. (Eigenes Modul, damit die Migration schlank bleibt und der Katalog testbar ist.)
- [x] Smoke-Test `backend/tests/test_classification_seed.py`: frische DB → Seed-Kategorien zählen + Stichprobe Label.
- [ ] `docs/models.md` Eintrag für die drei Tabellen vormerken (Voll-Update in Phase 6).

## Report-Back

**Status:** complete (2026-07-02).

- Modelle: `ClassificationCategory`, `ClassificationLabel`, `AssetClassification` in
  `backend/photofant/db/models.py` — exakt nach Kontrakt, inkl. `ON DELETE CASCADE`
  auf `classification_label.category_id` und `asset_classification.label_id`.
- Migration `0029_classification.py` (Nummer korrigiert von `0010` auf `0029`,
  siehe Checkliste) legt Tabellen + Indizes an und seedet den Konzept-Katalog über
  `insert_seed_catalog()`.
- Seed-Katalog (`backend/photofant/classification/seed.py`): 11 Kategorien
  (6 single, 5 multi — exakt nach AK #4), 128 Labels gesamt. `clip_prompts` überall
  `NULL` (Template greift), `wd14_tags` gesetzt wo ein Danbooru/WD14-Tag eindeutig
  zuordenbar ist (u.a. Stil-, Eigenschaften-, Franchise-/Charakter-Labels), sonst
  `NULL` (rein CLIP) — konservativ gehalten, keine geratenen Tag-Namen.
- Smoke-Test: 5 Testfälle grün (Kategorie-/Label-Anzahl, builtin/enabled,
  Single/Multi-Zuordnung, Stichprobe „Anime" → `["anime"]`).
- `ruff check` grün; `mypy --strict` auf `seed.py` sauber. `models.py` trägt 5
  vorbestehende „unused type: ignore"-Fehler (nicht von dieser Phase verursacht,
  vor der Änderung bereits vorhanden — Repo-weite Altlast, nicht Teil dieser AK).
- Finding für Phase 3 in `FINDINGS.md`: SQLite cascadet nur mit
  `PRAGMA foreign_keys=ON`, das global (noch) nicht gesetzt ist — DELETE-Endpoints
  müssen Kind-Zeilen explizit räumen.
- `docs/models.md` noch offen — bewusst auf Phase 6 verschoben (Voll-Update dort).
