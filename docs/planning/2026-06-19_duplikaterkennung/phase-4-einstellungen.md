# Phase 4 — Einstellungen: Threshold-Slider

> **Voraussetzung:** `2026-06-19_einstellungen-refactoring` abgeschlossen — die Verarbeitung-Sektion
> ist dann eine eigenständige Child-Komponente, in die wir direkt und sauber einbauen.

## Kontext (vor Implementierung lesen)

- `docs/planning/2026-06-19_einstellungen-refactoring/README.md` — Kontrakt der refactorierten Struktur
- `frontend/src/app/features/einstellungen/` — nach Refactoring: Shell + Child-Komponenten
- `backend/photofant/settings.py` — `dupe_threshold` (Phase 1)
- Angular-Konventionen: `docs/conventions/angular.md`

## Akzeptanzkriterien

1. In der Einstellungen-Sektion "Verarbeitung" gibt es einen Slider "Ähnlichkeitsschwelle" (Hamming-Distanz, Range 0–20, Default 10).
2. Slider zeigt aktuellen Wert numerisch (z. B. "10 — mittlere Empfindlichkeit").
3. Änderung wird via `PATCH /api/settings` persistiert (bestehender Settings-Endpunkt).
4. Kurze Erklärung inline: "0 = nur Identisches, 20 = sehr ähnliche Bilder" — als Helper-Text direkt unter dem Slider, kein Modal/Tooltip-Zwang.
5. Keine Neuimport oder Rescan wird automatisch ausgelöst — nur zukünftige Imports/Scans nutzen den neuen Wert.

## Checkliste

### Frontend

- [x] Verarbeitung-Child-Komponente öffnen (nach Refactoring: `verarbeitung.ts` o.ä.)
- [x] Slider-Control für `dupe_threshold` hinzufügen (HTML range input oder vorhandene Setting-Primitive)
- [x] Signal/Store verdrahten: Wert laden (`GET /api/settings`), speichern (`PATCH /api/settings`)
- [x] Helper-Text: "0 = nur identische Bilder · 20 = sehr ähnliche Bilder einschließen"
- [x] Numerische Anzeige neben Slider (gebunden an Slider-Wert, kein Blur nötig)

### Docs

- [x] Keine neue Setting-Primitive — bestehendes Pattern weiterverwendet (kein Docs-Update nötig)

## Report-Back

`linkedSignal` für die Live-Anzeige während des Ziehens genutzt (Angular 19) — fällt automatisch auf den Store-Wert zurück wenn die PATCH-Response eintrifft. Label computed: "0–4 = nur fast identisch / 5–9 = geringe Toleranz / 10–14 = mittlere Empfindlichkeit / 15–20 = hohe Toleranz".
