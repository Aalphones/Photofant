# Phase 6 — Docs & ADR-010

**Tier:** mechanisch (Doc-only, kein neuer Code)

## Kontext (vor Start lesen)

- [`docs/models.md`](../../../docs/models.md), [`docs/routes.md`](../../../docs/routes.md), [`docs/code-map.md`](../../../docs/code-map.md) — die Code-Referenz-Docs (Sync-Pflicht).
- [`docs/decisions/`](../../../docs/decisions/) — ADR-Stil (10-Zeilen: Kontext / Optionen / Entscheidung / Konsequenzen). Nächste freie Nummer: **ADR-010** (007 von P11, 009 von P17 reserviert).
- [`docs/glossary.md`](../../../docs/glossary.md), [`docs/PROJECT.md`](../../../docs/PROJECT.md).

## Akzeptanzkriterien

1. `docs/models.md`: die drei neuen Tabellen + die Belegung von
   `ProcessingLedger.classified` dokumentiert.
2. `docs/routes.md`: `/classification/*` CRUD, `GET /assets`-Filter
   `classification` + Facets, `AssetDetailDto.classifications`, der
   `"categories"`-Rerun-Step.
3. `docs/code-map.md`: neue Zeile „Bildklassifizierung" (vertikaler Slice) —
   `features/einstellungen/klassifizierung/`, `store/classification/`,
   `services/classification.service.ts` · `api/classification.py`,
   `classification/engine.py`, `jobs/classification_job.py`.
4. `docs/decisions/010-bildklassifizierung-engine.md`: Entscheidung für die
   CLIP+WD14-Fusion über **gespeicherte** Signale (Reuse statt Modell-Neulauf),
   single/multi-Modus, Reuse des `classified`-Ledger-Flags.
5. `docs/glossary.md`: Begriffe „Kategorie", „Label", „Klassifizierung",
   „Fusion" (eine Bedeutung je Begriff).
6. `docs/PROJECT.md`: Meilenstein-Eintrag; Backlog-Tabelle um P18 ergänzt bzw.
   nach Umsetzung als erledigt markiert.
7. Konzept liegt als `KONZEPT.md` im Plan-Ordner (bereits verschoben) — beim
   Archivieren mit dem Plan zusammen verschieben.

## Checkliste

- [x] `models.md` aktualisiert.
- [x] `routes.md` aktualisiert.
- [x] `code-map.md` Slice ergänzt.
- [x] `decisions/010-bildklassifizierung-engine.md` angelegt.
- [x] `glossary.md` Begriffe ergänzt.
- [x] `PROJECT.md` Meilenstein/Backlog.

## Report-Back

Alle sechs Doc-Ziele umgesetzt, Code-Abgleich (nicht nur Plan-Kontrakt) für jede Datei
durchgeführt. Eine Abweichung vom vorgezeichneten Soll-Stand: `docs/glossary.md` existierte
im Projekt **noch gar nicht** (Standard-Struktur laut globalem Docs-Workflow, aber nie
angelegt) — neu erstellt mit den vier geforderten Begriffen statt einer bestehenden Datei
ergänzt. `docs/PROJECT.md`s Backlog-Tabelle war bereits vor dieser Phase veraltet (mehrere
dort gelistete Pläne sind laut `STATE.md` längst archiviert); bewusst nur P18 ergänzt statt
die ganze Tabelle in dieser mechanischen Phase zu sanieren — als Hinweiszeile im Dokument
vermerkt.
