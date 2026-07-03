# Editor — Basis-Bearbeitung: Fixes & Orientierungs-Überschreiben

**Angelegt:** 2026-07-03 · **Profil:** private (lean) · eingeschoben vor P18-Phase-2.

Ausgangslage: die „einfachen" Editier-Optionen speichern nicht, Crop-Ratios greifen
nicht, die Leiste ist zu eng — und Drehen/Spiegeln soll die Quelle überschreiben statt
neue Edits anzulegen.

## Entscheidungen (mit User abgestimmt)

1. **Dreh/Spiegel-Regel:** *Nur-Orientierung überschreibt.* Enthält eine Edit-Session
   ausschließlich `rotate`/`mirror`-Schritte → Quelle wird direkt überschrieben, keine
   neue Version. Sobald ein Content-Edit (crop/pad/rembg/convert/smart_crop) dabei ist →
   wie bisher Versions-Pipeline. Bulk: eine Op = immer Überschreiben bei rotate/mirror.
2. **Original-Handling:** *Voll mit Metadaten-Refresh.* Beim Überschreiben eines
   Originals (instance) werden alle abhängigen Daten nachgezogen: content_hash, Maße,
   phash, file_size/format, Thumbnails neu; Gesichts-Boxen (`face.bbox`) mathematisch
   mitgedreht (bei 90/180/Spiegeln exakt, keine Neu-Erkennung); `processing_ledger`-Key
   auf neuen Hash umschreiben.

## Phasen

### Phase 1 — Speichern verdrahten (Frontend) ✅

Das Backend-`/save` (`api/edit_sessions.py:save_session`) ist fertig, wird nur nie
aufgerufen. `Editor.onSave` loggt bloß in die Konsole.

- `services/edit-session.service.ts`: `save(sessionKey, mode)` → `POST …/save`.
- `store/editor/`: Action `Save`/`Save Success`/`Save Failure`, `saving`-Flag im Reducer,
  `onSave$`-Effect.
- `features/editor/editor.ts`: `onSave` dispatcht; auf `saveSuccess` Editor schließen
  (goBack / closed-Output).
- `models/edit-session.model.ts`: `SaveMode`-Typ zentral.

**Risiko/Follow-up:** Nach Save muss die Galerie/Lightbox die neue aktuelle Version zeigen
(Refresh-on-Return) — separat prüfen, nicht Teil dieser Phase.

### Phase 2 — Crop-Ratio + Leisten-Breite (Frontend) ✅

- `crop-overlay.ts`: Seitenverhältnis in **Pixelraum** rechnen. Effektives Prozent-Ratio
  = Ziel-Ratio × naturalH / naturalW. Betrifft `snapToRatio`, `applyRatioConstraint`,
  `onDragMove`. Guard, solange `naturalSize` nicht geladen.
- `editor.scss`: linke Werkzeug-Spalte auf Desktop verbreitern, mehr Innenabstand.

### Phase 3 — Orientierung überschreibt Quelle (Backend, Risiko-Phase) ✅

- `media/ops.py` oder neu: Helfer „ist Schrittliste nur Orientierung?" + bbox-Transform
  für rotate(cw/ccw/180)/mirror(h/v).
- `api/edit_sessions.py:save_session`: wenn Session nur Orientierung → Quelle
  (`source_path`) in place überschreiben, keine Version. Pro kind:
  - **version**: Datei überschreiben, `params` (width/height) updaten, Thumbnails neu.
  - **face**: crop-Datei überschreiben, `resolution`/`phash` updaten, Thumbnail neu.
  - **instance**: Original überschreiben + voller Metadaten-Refresh (siehe Entscheidung 2).
- `jobs/bulk_edit_job.py`: bei `op ∈ {rotate, mirror}` → Quelle überschreiben statt
  Version anlegen (gleiche kind-Logik, hier nur instance).
- Frontend: Save-Modal-Text/-Fluss für Orientierungs-only anpassen (überschreibt Datei,
  kein overwrite/new_copy-Choice nötig).
- Tests: backend Move/Ops-Tests (Pflicht-Ausnahme private), inkl. bbox-Transform &
  Hash-Refresh.

**Umsetzung — Abweichungen von der ursprünglichen Beschreibung (mit User abgestimmt,
2026-07-03):**

- **Mehrpersonen-Fotos (mehrere `AssetInstance` je `Asset`):** war im Plan nicht bedacht.
  `Asset.content_hash/width/height/phash` + der Galerie-Thumbnail sind pro `asset_id`
  geteilt (nicht pro Instanz) — reines Überschreiben der editierten Instanz hätte die
  Kopien anderer Personen unbemerkt aus dem Takt gebracht. Entscheidung: **alle** aktiven
  Instanzen eines Assets werden mittransformiert, danach genau einmal aus der editierten
  Instanz die Asset-Zeile aktualisiert. Details/Begründung: Docstring in
  `media/orientation_overwrite.py`.
- **Gesichts-Boxen:** wie geplant rein mathematisch transformiert (kein Neu-Detect).
  Nur `Face.bbox` (Koordinaten im Foto) wird aktualisiert — die Crop-**Dateien** der
  betroffenen Faces bleiben unangetastet und zeigen bis zum nächsten Reconcile/Rebuild
  die alte Ausrichtung. Bewusst außerhalb des Scopes (User-Entscheidung), bekanntes
  Follow-up bei Bedarf.
- **Bulk-Edit:** `bulk_edit_job.py` löst pro `asset_id` mehrere `AssetInstance`-Zeilen auf
  (eine je Person) — bei Orientierung-only wird pro Asset einmal transformiert (dedupe),
  nicht pro Zeile.

## Status

Phase 1 + 2 + 3 committet. Editor-Basis-Fixes damit fertig. Weiter mit P18 (siehe STATE.md).
