# Phase 4 — Frontend-Einstellungen

**Tier:** standard  
**Status:** complete

---

## Kontext (was vorher lesen)

- `frontend/src/app/models/config.model.ts` — `ProcessingConfig`, `PROCESSING_CONFIG_DEFAULTS`
- `frontend/src/app/store/models/models.effects.ts` — `KEY_MAP`, `extractProcessingConfig`
- `frontend/src/app/features/einstellungen/verarbeitung/verarbeitung.ts` + `.html` + `.scss`
- `frontend/src/app/services/person.service.ts` — `searchDuplicates` Signatur
- `frontend/src/app/features/personen/dupe-check-dialog/dupe-check-dialog.ts`
- Kontrakt-Sektion in README — Settings-Keys und Frontend-Felder
- Phase 3 muss abgeschlossen sein (API akzeptiert neue Parameter)

---

## Abnahme-Kriterien

- [x] Einstellungsseite zeigt unter „Duplikaterkennung" drei Steuerungen:
  - Toggle: „Genaue Duplikate erkennen" (pHash, mit Erklärtext: findet pixelidentische Dateien)
  - Toggle: „Ähnliche Bilder erkennen" (CLIP, mit Erklärtext: was CLIP findet)
  - Slider: „Ähnlichkeits-Schwelle" (70–99 %, nur sichtbar wenn CLIP aktiv)
- [x] Jede Steuerung hat einen Erklärtext — keine Fachbegriffe, kein „Hamming"
- [x] CLIP-Schwelle wird im UI als Prozent angezeigt (z. B. 85 %), intern als Cosine-Distance (0.15) gespeichert
- [x] Deaktivierter Toggle blendet den zugehörigen Slider aus (kein Layout-Loch)
- [x] `ProcessingConfig` enthält `dupePhashEnabled`, `dupeClipEnabled`, `dupeClipThreshold`
- [x] Store, Effects und Selector sind konsistent mit den neuen Feldern
- [x] `searchDuplicates` in `PersonService` übergibt `clipThreshold` an die API
- [x] `DupeCheckDialog` liest beide Schwellen aus dem Store

---

## Checkliste

### Modell & Store

- [x] `config.model.ts` — `ProcessingConfig` erweitern:
  ```typescript
  dupePhashEnabled:  boolean
  dupeClipEnabled:   boolean
  dupeClipThreshold: number   // intern Cosine-Distance 0.05–0.30
  ```
- [x] `PROCESSING_CONFIG_DEFAULTS`: `dupePhashEnabled: true`, `dupeClipEnabled: true`, `dupeClipThreshold: 0.15`
- [x] `models.effects.ts` — `KEY_MAP` ergänzen:
  ```typescript
  dupePhashEnabled:  'dupe_phash_enabled',
  dupeClipEnabled:   'dupe_clip_enabled',
  dupeClipThreshold: 'dupe_clip_threshold',
  ```
- [x] `extractProcessingConfig` — drei neue Felder lesen (Boolean / Boolean / Number)

### verarbeitung.ts

- [x] `dupeClipThresholdDisplay = linkedSignal(...)` — analog `dupeThresholdDisplay` für CLIP-Slider
- [x] `dupeClipThresholdLabel = computed(...)` — zeigt Prozentzahl statt roher Distanz:
  - Intern `0.15` → UI-Display `85 %`, Berechnung: `Math.round((1 - value) * 100)`
- [x] Handler: `onDupePhashEnabledToggle()`, `onDupeClipEnabledToggle()`
- [x] Handler: `onDupeClipThresholdInput(target)`, `onDupeClipThresholdChange(target)`
  - `onDupeClipThresholdChange`: Eingabe ist Prozentzahl (70–99) → speichert `(100 - pct) / 100`
  - Clamp: `pct = Math.min(99, Math.max(70, pct))`

### verarbeitung.html

- [x] Sektion „Duplikaterkennung" neu strukturieren — 3 Zeilen statt 1:

  ```
  [Toggle] Genaue Duplikate erkennen  (pHash)
           "Findet pixelidentische Dateien — dieselbe Datei in zwei verschiedenen
            Ordnern oder unter unterschiedlichem Namen. Kein false positive möglich."

  [Toggle] Ähnliche Bilder erkennen  (CLIP)
           "Findet inhaltlich ähnliche Bilder: gleiche Szene aus einem anderen
            Blickwinkel, andere Belichtung oder Bearbeitung."
  [Slider] Ähnlichkeits-Schwelle (in %)  ← nur wenn CLIP aktiv
           "99 % = nur fast identische Motive · 70 % = auch entfernt ähnliche einschließen"
  ```

- [x] Kein Slider für pHash (distance == 0 ist fix, keine Konfiguration nötig)
- [x] Bedingte Sichtbarkeit: `@if (processingConfig().dupeClipEnabled)` um CLIP-Slider
- [x] Slider-Wert CLIP: `[value]="Math.round((1 - processingConfig().dupeClipThreshold) * 100)"`
  - `min="70"` `max="99"` `step="1"`

### Service & Dialog

- [x] `PersonService.searchDuplicates(personId, phashThreshold, clipThreshold)` — Signatur erweitern
  - Body schickt `{ person_id, threshold: phashThreshold, clip_threshold: clipThreshold }`
- [x] `DupeCheckDialog` — `processingConfig().dupeClipThreshold` an `searchDuplicates` übergeben

---

## Report-Back

Wie geplant umgesetzt, keine Abweichungen. Alter Hamming-Slider (`dupeThresholdDisplay`/`dupeThresholdLabel`/`onDupeThresholdInput`/`onDupeThresholdChange`) aus `verarbeitung.ts`/`.html` entfernt — `dupeThreshold` bleibt als Altlast im Typ (wird noch intern an `PersonService.searchDuplicates` als `phashThreshold` weitergereicht, da der Person-Duplikate-Endpunkt seine eigene Hamming-Schwelle behalten hat, siehe Phase-3-Kontrakt `duplicates.py`). `tsc --noEmit` lief sauber durch.
