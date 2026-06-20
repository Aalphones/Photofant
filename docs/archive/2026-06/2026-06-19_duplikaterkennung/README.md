# Duplikaterkennung — pHash + Review-Queue Tab 2

> Status: complete (alle 6 Phasen) · Eigentümer: Backend + Frontend
> **Reihenfolge: NACH `2026-06-19_einstellungen-refactoring`** — Phase 4 legt einen neuen Settings-Child
> an; besser auf dem refactorierten Fundament bauen als im Monolith.

Beim Import werden mutmaßliche Duplikate (gleiches Bild, leicht bearbeitet; andere Auflösung; verlustbehaftetes Re-Export) nicht mehr hart geblockt, sondern zur Entscheidung in die Review-Queue eingestellt. Basis ist ein **pHash (Perceptual Hash)** — ein 64-Bit-DCT-Fingerabdruck, der kleine Edits toleriert und per Hamming-Distanz verglichen wird. Braucht kein ML-Modell.

Zwei Einstiegspunkte:
- **Automatisch**: jeder Import berechnet pHash + prüft gegen Bestand → erzeugt Review-Items
- **On-Demand**: Scan-Job (via Review-Tab oder Action-Bar-Bulkauswahl) + Lightbox-Einzelsuche

## Overview

| # | Phase | Rating | Status |
|---|---|---|---|
| 1 | [pHash-Infra + Migration](phase-1-phash-infra.md) | heikel | complete |
| 2 | [Import-Pipeline Auto-Detection](phase-2-import-auto.md) | standard | complete |
| 3 | [On-Demand-Scan-Job + Review-API](phase-3-scan-und-api.md) | standard | complete |
| 4 | [Einstellungen: Threshold-Slider](phase-4-einstellungen.md) | mechanisch | complete |
| 5 | [Frontend: Review-Tab Duplikate](phase-5-review-tab.md) | heikel | complete |
| 6 | [Frontend: Lightbox + Action-Bar](phase-6-lightbox-actionbar.md) | standard | complete |

## Kontrakt

### Neue DB-Spalten (`asset`)

| Spalte | Typ | Bedeutung |
|---|---|---|
| `phash` | `INTEGER` nullable | 64-Bit pHash (imagehash DHash); NULL bis pHash-Job gelaufen |
| `original_id` | `INTEGER FK → asset.id` nullable | gesetzt wenn dieses Asset ein Edit eines anderen ist |

### Neue Tabelle `review_item`

| Spalte | Typ | Bedeutung |
|---|---|---|
| `id` | INTEGER PK | |
| `type` | TEXT | `dupe_candidate` (erweiterbar für P7 Gesichts-Review) |
| `asset_a_id` | INTEGER FK → asset.id | immer der mit der kleineren ID |
| `asset_b_id` | INTEGER FK → asset.id | immer der mit der größeren ID |
| `phash_distance` | INTEGER | Hamming-Distanz (0–63) |
| `created_at` | DATETIME | UTC naive |
| `resolved_at` | DATETIME | nullable |
| `resolution` | TEXT | nullable: `a_is_original` · `b_is_original` · `delete_a` · `delete_b` · `dismiss` |

Unique-Constraint: `(type, asset_a_id, asset_b_id)` — kein Doppeleintrag pro Paar.

### API-Endpunkte

```
GET  /api/review/dupes                         → DupePair[]  (nur unresolved)
PATCH /api/review/dupes/{id}                   → body: { resolution }
POST /api/jobs/dupe-scan                       → body: { scope: 'all' | 'selection', asset_ids?: number[] }
GET  /api/assets/{id}/similar                  → SimilarAsset[]  (für Lightbox, ad-hoc)
```

### Frontend-Typen (NgRx / API-Kontrakt)

```ts
interface DupePair {
  id: number;
  assetA: AssetSummary;
  assetB: AssetSummary;
  pHashDistance: number;
  createdAt: string;
}
type DupeResolution = 'a_is_original' | 'b_is_original' | 'delete_a' | 'delete_b' | 'dismiss';
```

### Neues Setting

`dupe_threshold: number` — Hamming-Distanz-Schwelle (0–20, Default 10). In `settings.py` + `settings.example.json`.

## Architektur-Entscheidung

**ADR-006** (`docs/decisions/006-phash-duplikaterkennung.md`) — pHash als primäre Ähnlichkeits-Metrik (Phase 1).

## 🟡 Risiken

- **Batch-Import-Flood:** 200 Bilder auf einmal können viele Paare erzeugen. Gegenmaßnahmen: Unique-Constraint verhindert Doppeleinträge; Threshold-Default 10 filtert viele False-Positives heraus.
- **pHash bei extremer Komprimierung:** sehr kleine Thumbnails oder stark komprimierte JPEGs können hohe Hamming-Distanz auch bei identischem Motiv erzeugen → Threshold in Settings anpassbar.
- **On-Demand-Scan N²:** Für N=10.000 Assets ca. 50M Vergleiche in Python → 5-15 Sekunden Job-Laufzeit. Akzeptabel als Hintergrund-Job mit Progress-Bar; kein UI-Block.

## Finale Akzeptanzkriterien

1. Import eines Bildes, das dem Bestand ähnlich ist (Hamming ≤ Threshold), erzeugt einen `review_item`-Eintrag.
2. Review-Queue zeigt Tab "Duplikate" mit Paar-Liste; alle 5 Aktionen (A=Original, B=Original, A löschen, B löschen, Beide behalten) funktionieren und persistieren.
3. On-Demand-Scan-Job läuft durch, zeigt Progress, füllt Review-Queue mit gefundenen Paaren.
4. Lightbox-Button "Ähnliche Bilder" öffnet Ergebnis-Overlay für das aktuelle Bild.
5. Action-Bar-Bulk-Aktion "Duplikate prüfen" triggert Scan auf Auswahl und navigiert zur Review-Queue.
6. Threshold-Slider in Einstellungen → Verarbeitung; Änderung wirkt ab dem nächsten Scan/Import.
7. `asset.original_id` wird bei A=Original- / B=Original-Entscheidung korrekt gesetzt.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] 2 ähnliche Bilder importieren → Review-Queue-Badge zeigt 1 neuen Eintrag.
- [ ] Review-Tab öffnen → Tab "Duplikate" sichtbar; Paar erscheint mit Ähnlichkeitswert.
- [ ] "A ist Original" wählen → B erhält `original_id = A.id`; Paar verschwindet aus Queue.
- [ ] Scan-Button im Duplikat-Tab klicken → Job erscheint in Job-Dock mit Progress.
- [ ] Lightbox öffnen → Button "Ähnliche Bilder" sichtbar; Klick zeigt Treffer-Overlay.
- [ ] Mehrere Bilder in Galerie selektieren → Action-Bar zeigt "Duplikate prüfen"; Klick triggert Job.
- [ ] Threshold in Einstellungen auf 4 senken → nächster Import findet weniger Paare.

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups
