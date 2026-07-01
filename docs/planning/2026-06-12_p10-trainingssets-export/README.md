# P10 — Trainingssets & Export (Stage 6)

> Status: geparkt · Quelle: [Konzept](../../Konzept-Photofant.md) §9, §11 (Export) · Abhängigkeiten: P5, P6 (P7-Personen und P8-Editor werten auf, sind aber nicht Pflicht)

Die Organisations- und Export-Endstufe: manuelle Alben rund, Lineage-Gruppierung, Trainingssets mit Statistiken und Caption-Tools, Near-Dupe-Pflege, alle Export-Workflows inkl. Sidecar-`.txt` und Train/Val-Split.

## Overview

| Phase | Topic | Rating | Status |
|---|---|---|---|
| 1 | [Lineage & Collections-Ausbau](phase-1-lineage-collections.md) | standard | complete |
| 2 | [Trainingssets & Statistiken](phase-2-trainingssets-stats.md) | standard | pending |
| 3 | [Caption-Tools & Near-Dupes](phase-3-caption-tools-dupes.md) | standard | pending |
| 4 | [Export-Workflows](phase-4-export.md) | standard | pending |

## Kontrakt (Backend ↔ Frontend)

- **Lineage:** `GET /api/assets/{id}/lineage` → Original + alle Versionen/Faces als Baum; Galerie-Gruppierung „Original/Face/Edit" nutzt das.
- **Trainingsset = `collection.kind = 'training_set'`** mit `settings` JSON (trigger_word, prefix, suffix, split_ratio); **`GET /api/collections/{id}/stats`** → `{ framing: {...}, tag_frequencies: [...], quality_histogram: [...], ar_buckets: [...], near_dupe_rate }` (Aspect-Ratio-Buckets Kohya-Style).
- **`POST /api/collections/{id}/captions`** — `{ action: "trigger_word" | "prefix" | "suffix" | "find_replace", params }` → wirkt auf `caption_override` aller Items (Original-Caption bleibt unangetastet); `PATCH /api/collections/{id}/items/{asset_id}` — `{ caption_override }`.
- **`GET /api/collections/{id}/duplicates`** — Near-Dupe-Paare (pHash) fürs Links-Rechts-Review; Entscheidung pro Paar: `keep_left | keep_right | keep_both` (Verworfene → Papierkorb).
- **`POST /api/collections/{id}/export`** — `{ sidecar: "tags" | "caption" | "both" | null, split_ratio?, target_dir }` → Queue-Job; Sidecars sind reine Export-Artefakte (Konzept §9 — nie in der Galerie-Ablage).
- **`POST /api/export/favourites/random`** — `{ sets: number, per_set: number, target_dir }` → distinct ohne Duplikate, Dateinamen mit Person; **`POST /api/export`** — aktueller Filter / Gruppierung / Collection (`{ scope, target_dir }`).
- **„Im Dateisystem anzeigen":** `POST /api/assets/{id}/reveal` (Explorer öffnen — einzige erlaubte Shell-Interaktion).

## Finale Akzeptanzkriterien

1. Galerie-Gruppierung nach Lineage zeigt Original + Ableitungen als Einheit.
2. Trainingsset-View: Statistik-Dashboard (Framing-/Tag-/Qualitäts-/Bucket-Verteilung, Near-Dupe-Quote), Editier-Funktionen (Tags/Caption-Override pro Bild), Upscale/Edit aus dem Set heraus (wenn P8/P9 da).
3. Caption-Tools wirken über das ganze Set (Trigger-Word voran, Prefix/Suffix, Find-Replace) — nur auf Overrides, Galerie-Daten unangetastet.
4. Near-Dupe-Review im Links-Rechts-Vergleich, Entscheidungen wirken wie beschriftet.
5. Export erzeugt korrekte Sidecar-`.txt` (Tags/Caption/beides wählbar), optional Train/Val-Split in getrennte Ordner; Favoriten-Exporte (nach Person sortiert, Zufalls-Sets distinct) funktionieren.
6. Alle Exporte laufen als Queue-Jobs mit Fortschritt.

## Smoke-Checkliste (User, am Plan-Ende)

- [ ] Trainingsset aus ~50 Bildern bauen → Stats plausibel (Buckets, Framing)
- [ ] Trigger-Word + Suffix übers Set → Stichprobe der Overrides stimmt, Galerie-Captions unverändert
- [ ] Near-Dupe-Review: ein Paar links behalten → rechtes im Papierkorb
- [ ] Export mit „beides" + 90/10-Split → Ordnerstruktur, `.txt`-Inhalte und Verteilung stimmen
- [ ] 3×20 Zufalls-Favoriten exportieren → keine Duplikate über die Sets, Personen-Namen im Dateinamen

## Summary

## Files touched

## Commits

## Deviations from plan

## Follow-ups
