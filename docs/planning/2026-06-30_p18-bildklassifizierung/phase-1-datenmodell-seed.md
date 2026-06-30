# Phase 1 — Datenmodell & Seed-Katalog

**Tier:** heikel (Schema-Entscheidung, Migration, Seed-Daten)

## Kontext (vor Start lesen)

- [`backend/photofant/db/models.py`](../../../backend/photofant/db/models.py) — bestehende Tabellen, Stil der Mapped-Columns. `ProcessingLedger.classified` existiert hier schon ungenutzt.
- [`backend/alembic/versions/0009_classified_flag.py`](../../../backend/alembic/versions/0009_classified_flag.py) — Vorlage für eine Migration; nächste Nummer ist `0010`.
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

- [ ] `db/models.py`: `ClassificationCategory`, `ClassificationLabel`, `AssetClassification` ergänzen (Stil der bestehenden Modelle matchen).
- [ ] `alembic/versions/0010_classification.py`: `create_table` ×3 + Indizes; `down_revision` auf `0009` setzen.
- [ ] Seed-Daten als Python-Konstante (`backend/photofant/classification/seed.py`) — Liste aus dem Konzept; in der Migration eingespielt. (Eigenes Modul, damit die Migration schlank bleibt und der Katalog testbar ist.)
- [ ] Smoke-Test `backend/tests/test_classification_seed.py`: frische DB → Seed-Kategorien zählen + Stichprobe Label.
- [ ] `docs/models.md` Eintrag für die drei Tabellen vormerken (Voll-Update in Phase 6).

## Report-Back
