# P12 — Gesichtserkennung: Konfigurierbare Parameter

**Status:** pending

Schwellwerte und Parameter der Gesichtserkennung sind derzeit größtenteils
hardcoded. Dieser Plan überführt alle sechs relevanten Tunables in
`settings.json` (Backend) und die Einstellungsseite (Frontend) — mit
Sliders, Zahleneingaben und Erklärungen ohne Fachbegriffe.

---

## Overview

| Phase | Thema | Tier | Status |
|---|---|---|---|
| 1 | Backend: Settings + Codepfade | standard | pending |
| 2 | Frontend: ProcessingConfig + UI | standard | pending |

---

## Kontrakt

### Settings-Keys (Backend → Frontend)

| settings.json Key | TypeScript-Feld | Typ | Default | Herkunft |
|---|---|---|---|---|
| `face_det_conf_threshold` | `faceDetConfThreshold` | `number` | `0.5` | **neu** (war `_CONF_THRESHOLD` in `buffalo_l.py`) |
| `face_det_iou_threshold` | `faceDetIouThreshold` | `number` | `0.45` | **neu** (war `_IOU_THRESHOLD` in `buffalo_l.py`) |
| `face_crop_padding` | `faceCropPadding` | `number` | `40` | **neu** (war `_FACE_PADDING_DEFAULT` in `face_job.py`) |
| `face_auto_threshold` | `faceAutoThreshold` | `number` | `0.6` | bereits in `settings.py`, nur Frontend fehlt |
| `face_review_threshold` | `faceReviewThreshold` | `number` | `0.45` | bereits in `settings.py`, nur Frontend fehlt |
| `face_min_cluster_size` | `faceMinClusterSize` | `number` | `3` | bereits in `settings.py`, nur Frontend fehlt |

---

## Phase 1 — Backend: Settings + Codepfade

**Tier:** standard

### Kontext (was vorher lesen)

- `backend/photofant/settings.py` — `AppSettings`, `SETTINGS_DEFAULTS`, `_EXPECTED_TYPES`
- `backend/photofant/inference/adapters/buffalo_l.py` — `_CONF_THRESHOLD`, `_IOU_THRESHOLD`,
  `detect()`, `_decode_scrfd_outputs()`, `_nms()`
- `backend/photofant/jobs/face_job.py` — `_FACE_PADDING_DEFAULT`, `_run_face_job()`

### Abnahme-Kriterien

- [ ] `settings.py` enthält `face_det_conf_threshold` (float, Default 0.5),
  `face_det_iou_threshold` (float, Default 0.45), `face_crop_padding` (int, Default 40)
- [ ] `buffalo_l.detect()` nimmt `conf_threshold` und `iou_threshold` als Parameter;
  `_run_face_job` liest sie aus settings und übergibt sie
- [ ] `face_job.py` liest `face_crop_padding` aus settings statt hardcoded Konstante
- [ ] Bestehende Keys `face_auto_threshold`, `face_review_threshold`, `face_min_cluster_size`
  bleiben unverändert

### Checkliste

#### settings.py

- [ ] `AppSettings` TypedDict — 3 neue Felder ergänzen:
  ```python
  face_det_conf_threshold: float   # SCRFD Mindest-Konfidenz
  face_det_iou_threshold:  float   # NMS-IoU-Schwelle
  face_crop_padding:       int     # Pixel-Rand beim Gesichtsausschnitt
  ```
- [ ] `SETTINGS_DEFAULTS` ergänzen:
  `'face_det_conf_threshold': 0.5`, `'face_det_iou_threshold': 0.45`, `'face_crop_padding': 40`
- [ ] `_EXPECTED_TYPES` ergänzen:
  `'face_det_conf_threshold': (float, int)`, `'face_det_iou_threshold': (float, int)`,
  `'face_crop_padding': int`

#### buffalo_l.py

- [ ] Modulkonstanten `_CONF_THRESHOLD` und `_IOU_THRESHOLD` entfernen
- [ ] `detect()` Signatur erweitern:
  ```python
  def detect(
      self,
      image: np.ndarray,
      conf_threshold: float = 0.5,
      iou_threshold: float = 0.45,
  ) -> list[dict]:
  ```
- [ ] `_decode_scrfd_outputs(...)` — `conf_threshold` als Parameter statt Modulkonstante nutzen
- [ ] `_nms(...)` — `iou_threshold` kommt bereits als Parameter rein (Signatur bereits korrekt,
  Aufruf in `_decode_scrfd_outputs` anpassen)

#### face_job.py

- [ ] `_FACE_PADDING_DEFAULT` Konstante entfernen
- [ ] `_run_face_job` — settings einmal lesen, Werte an Aufrufstellen weitergeben:
  ```python
  from photofant.settings import load_settings
  settings      = load_settings()
  padding       = int(settings.get('face_crop_padding', 40))
  conf_thresh   = float(settings.get('face_det_conf_threshold', 0.5))
  iou_thresh    = float(settings.get('face_det_iou_threshold', 0.45))

  faces = engine.detect(image, conf_threshold=conf_thresh, iou_threshold=iou_thresh)
  ...
  crop_np = _crop_square(image, bbox, padding)
  ```

🟡 Settings-Lesen (disk I/O) passiert einmal pro Asset-Job — vertretbar, kein Caching nötig.

---

## Phase 2 — Frontend: ProcessingConfig + UI

**Tier:** standard

### Kontext (was vorher lesen)

- `frontend/src/app/models/config.model.ts` — `ProcessingConfig`, `PROCESSING_CONFIG_DEFAULTS`
- `frontend/src/app/store/models/models.effects.ts` — `PROCESSING_CONFIG_KEY_MAP`,
  `extractProcessingConfig`
- `frontend/src/app/features/einstellungen/verarbeitung/verarbeitung.ts` + `.html`
- Phase 1 muss abgeschlossen sein (Backend akzeptiert neue Keys)

### Abnahme-Kriterien

- [ ] `ProcessingConfig` + Defaults enthalten alle 6 neuen Felder
- [ ] Store liest alle 6 aus der API-Response, schreibt per PATCH zurück
- [ ] Einstellungsseite → Gesichtserkennung zeigt 3 neue Untergruppen:
  Detektion (2 Slider), Zuschnitt (1 Zahleneingabe), Personen-Zuordnung (2 Slider + 1 Zahleneingabe)
- [ ] Jede Steuerung hat eine Erklärung ohne Fachbegriffe
- [ ] Slider-Beschriftung zeigt Live-Wert + kontextuellen Hinweis (analog `dupeThresholdLabel`)
- [ ] Warnhinweis wenn `faceReviewThreshold >= faceAutoThreshold`

### Checkliste

#### config.model.ts

- [ ] `ProcessingConfig` — 6 neue Felder ergänzen (alle `number`):
  ```typescript
  faceDetConfThreshold: number   // 0.1–0.9
  faceDetIouThreshold:  number   // 0.1–0.9
  faceCropPadding:      number   // 0–150 px
  faceAutoThreshold:    number   // 0.4–0.95
  faceReviewThreshold:  number   // 0.2–0.85
  faceMinClusterSize:   number   // 2–20
  ```
- [ ] `PROCESSING_CONFIG_DEFAULTS` ergänzen:
  `faceDetConfThreshold: 0.5`, `faceDetIouThreshold: 0.45`, `faceCropPadding: 40`,
  `faceAutoThreshold: 0.6`, `faceReviewThreshold: 0.45`, `faceMinClusterSize: 3`

#### models.effects.ts

- [ ] `PROCESSING_CONFIG_KEY_MAP` — 6 neue Einträge:
  ```typescript
  faceDetConfThreshold: 'face_det_conf_threshold',
  faceDetIouThreshold:  'face_det_iou_threshold',
  faceCropPadding:      'face_crop_padding',
  faceAutoThreshold:    'face_auto_threshold',
  faceReviewThreshold:  'face_review_threshold',
  faceMinClusterSize:   'face_min_cluster_size',
  ```
- [ ] `extractProcessingConfig` — 6 neue Felder lesen (alle `Number(...)` mit Fallback auf Default)

#### verarbeitung.ts

- [ ] 4 `linkedSignal`s für Slider-Live-Anzeige (analog `dupeThresholdDisplay`):
  ```typescript
  readonly faceDetConfDisplay    = linkedSignal(() => this.processingConfig().faceDetConfThreshold);
  readonly faceDetIouDisplay     = linkedSignal(() => this.processingConfig().faceDetIouThreshold);
  readonly faceAutoDisplay       = linkedSignal(() => this.processingConfig().faceAutoThreshold);
  readonly faceReviewDisplay     = linkedSignal(() => this.processingConfig().faceReviewThreshold);
  ```
- [ ] 4 `computed` Beschriftungen:
  - `faceDetConfLabel` — z. B. `0.3 — sehr sensibel (mehr Fehlalarme)` · `0.5 — ausgewogen` · `0.8 — nur eindeutige Gesichter`
  - `faceDetIouLabel` — z. B. `0.3 — streng (nur getrennte Rahmen)` · `0.45 — Standard` · `0.7 — viel Überlappung erlaubt`
  - `faceAutoLabel` — z. B. `0.5 — viele Auto-Zuweisungen` · `0.6 — ausgewogen` · `0.85 — nur sichere Treffer`
  - `faceReviewLabel` — z. B. `0.3 — große Review-Queue` · `0.45 — mittlere Grauzone` · `0.6 — wenig Vorschläge`
- [ ] `reviewBelowAutoWarning = computed((): boolean => this.processingConfig().faceReviewThreshold >= this.processingConfig().faceAutoThreshold)`
- [ ] Handler für 4 Slider (je `onInput` + `onChange`):
  `onFaceDetConfInput/Change`, `onFaceDetIouInput/Change`,
  `onFaceAutoInput/Change`, `onFaceReviewInput/Change`
- [ ] Handler für 2 Zahleneingaben (je `onChange`):
  `onFaceCropPaddingChange` (0–150, clamp), `onFaceMinClusterSizeChange` (2–20, clamp)

#### verarbeitung.html — Sektion Gesichtserkennung

Bestehende Zeile "Personen-Clustering starten" bleibt. Davor 3 neue Untergruppen einfügen:

```
[gruppen-label] Detektion
[gruppe]
  [Slider]       Erkennungsschwelle            min 0.10  max 0.90  step 0.05
    Sub: "Wie sicher das Modell sein muss, um ein Gesicht zu melden.
          Niedriger → mehr Treffer, mehr Fehlalarme.
          Höher → nur eindeutige Gesichter."

  [Slider]       Überlappungsfilter            min 0.10  max 0.90  step 0.05
    Sub: "Werden zwei Erkennungsrahmen als zu ähnlich eingestuft, bleibt nur
          der bessere. Höherer Wert → mehr Überlappung wird toleriert."

[gruppen-label] Zuschnitt
[gruppe]
  [Zahleneingabe] Rand um Gesicht             min 0  max 150  step 5  (px)
    Sub: "Pixel-Abstand rund um den erkannten Bereich.
          Mehr → mehr Kontext (Haare, Schultern sichtbar), weniger Zoom."

[gruppen-label] Personen-Zuordnung
[gruppe]
  [Slider]       Automatisch zuweisen ab       min 0.40  max 0.95  step 0.05
    Sub: "Liegt die Ähnlichkeit über diesem Wert, wird das Gesicht der Person
          direkt zugewiesen."

  [Slider]       Zur Prüfung vorschlagen ab    min 0.20  max 0.85  step 0.05
    Sub: "Liegt die Ähnlichkeit in diesem Bereich, landet das Gesicht in der
          Review-Queue. Muss kleiner sein als 'Automatisch zuweisen ab'."
    @if reviewBelowAutoWarning():
      Warnhinweis: "Dieser Wert liegt über 'Automatisch zuweisen' —
                    die Review-Queue hat keinen Effekt."

  [Zahleneingabe] Mindest-Cluster-Größe        min 2  max 20  step 1
    Sub: "Wie viele Gesichter eine Gruppe mindestens haben muss, damit das
          Clustering daraus eine Person anlegt."

[bestehend]
  [Button] Clustering starten
```

---

## Finale Abnahme-Kriterien

- [ ] Erkennungsschwelle verringern → mehr Gesichter in Testbild erkannt
- [ ] Crop-Padding erhöhen → gespeicherter Ausschnitt zeigt mehr Kontext
- [ ] Auto-Schwelle absenken → Gesicht wird ohne Review einer Person zugewiesen
- [ ] Review-Schwelle über Auto-Schwelle setzen → Warnhinweis erscheint sofort im UI

---

## Archiv-Footer

**Summary:** —
**Files touched:** —
**Commits:** —
**Deviations:** —
**Follow-ups:** —
