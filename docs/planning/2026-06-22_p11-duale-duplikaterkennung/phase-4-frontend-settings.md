# Phase 4 — Frontend-Einstellungen

**Tier:** standard  
**Status:** pending

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

- [ ] Einstellungsseite zeigt unter „Duplikaterkennung" drei Steuerungen:
  - Toggle: „Genaue Duplikate erkennen" (pHash, mit Erklärtext: findet pixelidentische Dateien)
  - Toggle: „Ähnliche Bilder erkennen" (CLIP, mit Erklärtext: was CLIP findet)
  - Slider: „Ähnlichkeits-Schwelle" (70–99 %, nur sichtbar wenn CLIP aktiv)
- [ ] Jede Steuerung hat einen Erklärtext — keine Fachbegriffe, kein „Hamming"
- [ ] CLIP-Schwelle wird im UI als Prozent angezeigt (z. B. 85 %), intern als Cosine-Distance (0.15) gespeichert
- [ ] Deaktivierter Toggle blendet den zugehörigen Slider aus (kein Layout-Loch)
- [ ] `ProcessingConfig` enthält `dupePhashEnabled`, `dupeClipEnabled`, `dupeClipThreshold`
- [ ] Store, Effects und Selector sind konsistent mit den neuen Feldern
- [ ] `searchDuplicates` in `PersonService` übergibt `clipThreshold` an die API
- [ ] `DupeCheckDialog` liest beide Schwellen aus dem Store

---

## Checkliste

### Modell & Store

- [ ] `config.model.ts` — `ProcessingConfig` erweitern:
  ```typescript
  dupePhashEnabled:  boolean
  dupeClipEnabled:   boolean
  dupeClipThreshold: number   // intern Cosine-Distance 0.05–0.30
  ```
- [ ] `PROCESSING_CONFIG_DEFAULTS`: `dupePhashEnabled: true`, `dupeClipEnabled: true`, `dupeClipThreshold: 0.15`
- [ ] `models.effects.ts` — `KEY_MAP` ergänzen:
  ```typescript
  dupePhashEnabled:  'dupe_phash_enabled',
  dupeClipEnabled:   'dupe_clip_enabled',
  dupeClipThreshold: 'dupe_clip_threshold',
  ```
- [ ] `extractProcessingConfig` — drei neue Felder lesen (Boolean / Boolean / Number)

### verarbeitung.ts

- [ ] `dupeClipThresholdDisplay = linkedSignal(...)` — analog `dupeThresholdDisplay` für CLIP-Slider
- [ ] `dupeClipThresholdLabel = computed(...)` — zeigt Prozentzahl statt roher Distanz:
  - Intern `0.15` → UI-Display `85 %`, Berechnung: `Math.round((1 - value) * 100)`
- [ ] Handler: `onDupePhashEnabledToggle()`, `onDupeClipEnabledToggle()`
- [ ] Handler: `onDupeClipThresholdInput(target)`, `onDupeClipThresholdChange(target)`
  - `onDupeClipThresholdChange`: Eingabe ist Prozentzahl (70–99) → speichert `(100 - pct) / 100`
  - Clamp: `pct = Math.min(99, Math.max(70, pct))`

### verarbeitung.html

- [ ] Sektion „Duplikaterkennung" neu strukturieren — 3 Zeilen statt 1:

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

- [ ] Kein Slider für pHash (distance == 0 ist fix, keine Konfiguration nötig)
- [ ] Bedingte Sichtbarkeit: `@if (processingConfig().dupeClipEnabled)` um CLIP-Slider
- [ ] Slider-Wert CLIP: `[value]="Math.round((1 - processingConfig().dupeClipThreshold) * 100)"`
  - `min="70"` `max="99"` `step="1"`

### Service & Dialog

- [ ] `PersonService.searchDuplicates(personId, phashThreshold, clipThreshold)` — Signatur erweitern
  - Body schickt `{ person_id, threshold: phashThreshold, clip_threshold: clipThreshold }`
- [ ] `DupeCheckDialog` — `processingConfig().dupeClipThreshold` an `searchDuplicates` übergeben

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
