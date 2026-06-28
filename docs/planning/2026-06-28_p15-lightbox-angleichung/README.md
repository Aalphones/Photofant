# P15 — Lightbox: Angleichung ans Design-Mockup

**Status:** pending

Ziel: Die Angular-Lightbox an `docs/design/js/detail.jsx` + `compare.jsx` +
`relation.jsx` angleichen. Alle sechs unten aufgelisteten Abweichungsbereiche
werden pro Phase abgearbeitet. Phase 1 (Backend) ist Voraussetzung für alle anderen.

---

## Abweichungen vom Mockup (vollständige Gap-Liste)

### A — Stage-Toolbar (Icon-Buttons)
**Mockup:** 4 kompakte Icon-only-Buttons im Stage-Bereich — Stern (Favorit),
Crop (Editor öffnen), Compare (VersionCompare-Modal), Download/Export.  
**Aktuell:** Alle Aktionen als Text-Buttons im Panel unter „Aktionen". Kein
Icon-Toolbar im Stage.

### B — Panel-Header
**Mockup:** Avatar des ersten erkannten Gesichts + Person-Name + Datum/Uhrzeit
(zweiZeilen). Stern-Icon rechts wenn Favorit.  
**Aktuell:** Nur `#ID` + Datum. Kein Avatar, kein Personenname.

### C — Gesichter-Sektion
**Mockup:**
- Position: direkt nach Caption + Tags, VOR Versionen
- Jede Zeile: Crop-Thumbnail (Rand grün bei manuell) + Name + Pencil-Icon + Alter/Score
- Darunter: Quick-Assign-Grid (5 Personen, Thumbnail + Vorname + Score)
- „Weitere Personen…"-Button → öffnet PersonPicker-Modal (Scrim + Modal mit Suche)
- **z-index Bug im Mockup:** PersonPicker-Modal liegt unter der Lightbox — muss in der
  Angular-Impl. höher sein als `.lb` (z-index > Lightbox-z-index)

**Aktuell:**
- Position: ganz unten im Panel
- Layout: Thumbnail + Badge (nur Name oder Score), kein Pencil, kein Alter
- Kein Quick-Assign-Grid; stattdessen inline expandierende Match-Liste
- Kein separates Modal; Personensuche inline

### D — Versionen-Sektion
**Mockup:**
- Version-Liste: Thumbnail + Label + „Aktiv"-Badge + Datum + Params (Strength, Modell)
- „Vergleichen"-Link in Section-Header → öffnet VersionCompare-Modal
- VersionCompare: Side-by-Side-Overlay, jede Seite mit Panel-Selektor (Tabs:
  Aktuell / Versionen / Original / Edits), Footer-Meta (Auflösung, Quelle, Datum)
- „Neue Version ergänzen" Drag-Drop-Button am Ende der Liste

**Aktuell:** Stub-Kommentar, komplett leer. Backend liefert in `AssetDetailDto`
nur `version_count` (int), keine `versions: VersionDto[]`-Liste.

### E — Beziehungen-Sektion
**Mockup:**
- Untersektion „Originalvorlage": Wenn gesetzt → Thumbnail-Zeile (#ID + „Original"-Tag
  + Caption + Bearbeiten + Entfernen). Wenn leer → „Original zuordnen"-Button.
- Untersektion „Verknüpfte Edits · N": Liste aller Edits mit Thumbnail + Source-Tag +
  Caption + Entfernen. „Edit verknüpfen"-Button → öffnet RelationBrowser-Modal.
- RelationBrowser: Vollbild-Modal mit Textsuche + Personen/Quelle/Framing-Filter +
  Bild-Grid. Einzel- oder Mehrfachauswahl.

**Aktuell:** Sektion komplett fehlend. `AssetDetailDto` hat kein `original_id`,
kein `linked_edits[]`. API-Endpunkt zum Setzen von `original_id` existiert
(`setAssetOriginal` in `AssetService`), aber Anzeige fehlt.

### F — Metadaten
**Mockup:** Quelle (editierbares Dropdown), Originalvorlage (Mini-Thumbnail-Chip
mit Pencil → OriginalPicker), Framing (editierbares Dropdown), Auflösung, Seiten-
verhältnis, Format, Größe, Qualität (farbiger Score „99 / 100"), Hash.

**Aktuell:** Dimensionen ✓, Format ✓, Größe ✓, Quelle (read-only) ✗, Datum ✓,
Hash ✓. Fehlt: Framing, Seitenverhältnis, Qualitätsscore, Quelle editierbar,
Originalvorlage-Chip, Framing editierbar.
Backend: `AssetDetailDto` braucht `quality: float | None`, `framing: str | None`.

---

## Phasen-Übersicht

| Phase | Thema | Tier | Status |
|---|---|---|---|
| 1 | Backend-Erweiterungen (Detail-DTO + Patch) | heikel | pending |
| 2 | Stage-Toolbar + Panel-Header | standard | pending |
| 3 | Gesichter-Redesign + PersonPicker-Modal | standard | pending |
| 4 | Versionen-Sektion + VersionCompare-Modal | standard | pending |
| 5 | Beziehungen-Sektion + RelationBrowser-Modal | standard | pending |
| 6 | Metadaten: editierbar + fehlende Felder | standard | pending |

---

## Kontrakt (Backend → Frontend)

### `AssetDetailDto` — neue Felder

```typescript
original_id:   number | null          // gesetztes Original dieses Assets
linked_edits:  AssetSummary[]         // Assets, deren original_id auf dieses zeigt
versions:      VersionDto[]           // alle Versionen (bisher nur version_count)
quality:       number | null          // 0.0–1.0, farbiger Score im UI
framing:       string | null          // 'close_up' | 'medium' | 'full_body' | null
```

### `PATCH /api/assets/{id}` — neue patchbare Felder

```python
source:       str | None    # 'original' | 'flux' | 'sdxl' | …
framing:      str | None
original_id:  int | None    # null = Zuordnung entfernen
```

---

## Abnahme-Kriterien (Gesamt)

- [ ] Stage-Toolbar zeigt 4 Icon-Buttons; Panel „Aktionen" entfällt oder wird kompakter
- [ ] Panel-Header zeigt Avatar des ersten Gesichts + Personenname
- [ ] Gesichter sind nach Caption/Tags, vor Versionen; Quick-Assign-Grid sichtbar
- [ ] PersonPicker-Modal liegt über der Lightbox (korrekte z-index-Hierarchie)
- [ ] Versionen-Sektion zeigt vollständige Liste mit Thumbnails + Badges
- [ ] VersionCompare-Modal öffnet sich, linke und rechte Seite wählbar
- [ ] Beziehungen-Sektion zeigt Original + Edits; RelationBrowser öffnet sich
- [ ] Metadaten: Quelle + Framing sind editierbar; Qualität + Seitenverhältnis sichtbar

---

## Archiv-Footer

**Summary:** —
**Files touched:** —
**Commits:** —
**Deviations:** —
**Follow-ups:** —
