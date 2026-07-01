# Phase 7 — Gesichter-Modus der Lightbox (Face als eigenständiges Ziel)

**Tier:** heikel
**Status:** complete

Ergänzt 2026-07-01. Setzt Phase 4 voraus (Versionen-Sektion muss generisch für
`instance_id`/`face_id` funktionieren — siehe dort `versions: VersionDto[]`).
Koordiniert sich mit P21 (Galerie: Stapel & Tab-Konsolidierung) — P21 verlinkt
beim Öffnen eines Face-Stapels auf genau diesen Modus.

---

## Kontext (was vorher lesen)

- `backend/photofant/api/faces.py` — bestehende Face-Endpunkte (`assign`, Liste); noch **kein**
  Detail-Endpunkt
- `backend/photofant/db/models.py` — `Face` (Spalte `asset_id` = Source-Asset), `Version`
  (XOR `instance_id`/`face_id`)
- `frontend/src/app/store/gallery/gallery.effects.ts:210` — `openFaceLightbox$`, verwirft
  aktuell die `faceId`
- `frontend/src/app/features/galerie/lightbox/lightbox.ts` + `.html` — bestehende Komponente,
  bekommt einen zweiten Eingabe-Modus statt einer zweiten Komponente
- `docs/planning/2026-06-28_p15-lightbox-angleichung/README.md` — Kontrakt-Sektion
  `GET /api/faces/{id}`

---

## Abnahme-Kriterien

- [x] Lightbox bleibt **eine** Komponente — kein zweiter Selector, kein Duplikat-Template
- [x] `openFaceLightbox({ faceId })` öffnet die Lightbox im Face-Modus auf dem Face-Bild
  (nicht mehr das umgebende Asset)
- [x] Face-Modus blendet aus: Caption-Sektion, Tags-Sektion, Gesichter-Sektion (A–C)
  (zusätzlich auch Aktionen/Metadaten/GenMeta — Begründung siehe Report-Back)
- [x] Face-Modus zeigt: Stage-Bild = aktuelle Face-Version, Versionen-Sektion (D) mit
  `face.versions`, eine „Quelle"-Zeile mit Link/Thumbnail auf `source_asset_id`
- [x] Klick auf „Quelle" navigiert zur Asset-Lightbox (voller Modus) des Source-Bilds
- [x] Fotos und Edits sind von diesem Modus **unberührt** — weiterhin voller Funktionsumfang
  (Caption, Tags, Gesichter-Zuweisung, Beziehungen, Metadaten)

---

## Checkliste

### Backend

- [x] `GET /api/faces/{id}` neu: liefert `FaceDetailDto` (Kontrakt siehe README) —
  `versions` per `SELECT * FROM version WHERE face_id = :id`, `source_asset_id = face.asset_id`
- [x] Geprüft: `PATCH /api/faces/{id}` für Favorit/Löschen nicht nötig — Face hat kein
  Favorit-Feld im Modell, Löschen deckt das bestehende `DELETE /api/faces/{id}` ab.

### Frontend — Lightbox-Modus

- [x] `lightboxKind: 'asset' | 'face'` + `lightboxFaceId` als neuer Store-State statt
  eines eigenen `LightboxTarget`-Typs (schlankere Umsetzung, gleiche Wirkung)
- [x] `faceDetail = toSignal(...)` lädt `FaceDetailDto` reaktiv anhand `lightboxFaceId`
  (parallel zu `detail` für Assets, nicht ersetzend)
- [x] Template-Sektionen (Aktionen/Metadaten/GenMeta/Caption/Tags/Gesichter) hinter
  `@if (!isFaceMode())` — Begründung siehe Report-Back
- [x] Versionen-Sektion nutzt neues `activeVersions()` (asset- oder face-Quelle je nach Modus)
- [x] Neue „Quelle"-Zeile im Face-Modus: Thumbnail + Klick → `openAssetLightbox({ assetId })`
- [x] `openFaceLightbox` wird direkt im Reducer gehandhabt (kein Roundtrip mehr nötig,
  da die Komponente `FaceDetailDto` selbst reaktiv nachlädt)

### Store / Actions

- [x] `galleryActions.openFaceLightbox` Payload ist jetzt `{ faceId, assetId }`, öffnet
  den Face-Modus auf `faceId`. Das alte Prefetch-Verhalten (Asset laden + öffnen) lebt
  unter neuem Namen `openAssetLightbox({ assetId })` weiter — siehe Report-Back.

---

## Report-Back

**Abweichung von der Checkliste:**
- Statt eines `LightboxTarget`-Union-Typs zwei einfache State-Felder (`lightboxKind`,
  `lightboxFaceId`) im Gallery-Store — gleiche Semantik, weniger Umbau am bestehenden
  `asset()`/`lightboxId`-Pfad.
- **Reduzierter Modus geht über A–C hinaus:** Aktionen, Metadaten, Generierungs-Metadaten
  und Beziehungen sind ebenfalls ausgeblendet, nicht nur Caption/Tags/Gesichter. Grund:
  `FaceDetailDto` hat keine Felder für Format/Auflösung/Qualität/Framing/Original/Edits —
  diese Sektionen hätten ohne Daten nur leer oder falsch gerendert. VersionCompare-Modal
  ebenfalls im Face-Modus ausgeblendet (AK verlangte nur, dass die Versionen-Liste
  sichtbar+navigierbar ist, nicht der Vergleich).
- **Chesterton's Fence — `openFaceLightbox` war ein Workaround:** Die Action wurde
  bisher von `onFaceLightboxOpenAsset` (in `galerie.ts`, Klick auf "Quelle" innerhalb
  des separaten `FaceLightbox`-Widgets im Face-Grid) missbraucht, um einen noch nicht
  geladenen Asset vorab zu holen und die normale Lightbox zu öffnen. Damit die
  Repurposing der Action (jetzt: Face-Modus) diesen Aufrufer nicht stillschweigend
  bricht, wurde dafür eine neue, gleichwertige Action `openAssetLightbox({ assetId })`
  mit demselben Fetch-dann-Öffnen-Effekt angelegt und der Aufrufer umgehängt.
- **Nicht angefasst (bewusst außerhalb des Scopes):** Das separate `FaceLightbox`-Widget
  (`features/galerie/face-lightbox/`) für die Face-Grid-Ansicht bleibt unverändert — laut
  README-Abschnitt G verlinkt erst P21 ("Galerie: Stapel & Tab-Konsolidierung") das Öffnen
  eines Face-Stapels auf den neuen Gesichter-Modus. Diese Phase liefert nur die Fähigkeit.

**Tests:** 4 neue Backend-Tests (`backend/tests/test_faces_api.py`) für den neuen
Endpunkt (Detail mit Versionen, Face ohne Person/Versionen, 404, Routing-Kollision mit
`/faces/gallery`). Voller Backend-Testlauf danach unverändert (12 vorbestehende, von
dieser Änderung unabhängige Failures in `test_comfyui_run.py`/`test_caption_config.py`
— per `git stash` verifiziert, dass sie auch ohne diese Änderung fehlschlagen).
Frontend: `tsc --noEmit` und `ng build` sauber; keine Frontend-Unit-Tests laut
private-Profil-Konvention (Smoke-Check folgt durch den User).
