# Phase 7 — Gesichter-Modus der Lightbox (Face als eigenständiges Ziel)

**Tier:** heikel
**Status:** pending

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

- [ ] Lightbox bleibt **eine** Komponente — kein zweiter Selector, kein Duplikat-Template
- [ ] `openFaceLightbox({ faceId })` öffnet die Lightbox im Face-Modus auf dem Face-Bild
  (nicht mehr das umgebende Asset)
- [ ] Face-Modus blendet aus: Caption-Sektion, Tags-Sektion, Gesichter-Sektion (A–C)
- [ ] Face-Modus zeigt: Stage-Bild = aktuelle Face-Version, Versionen-Sektion (D) mit
  `face.versions`, eine „Quelle"-Zeile mit Link/Thumbnail auf `source_asset_id`
- [ ] Klick auf „Quelle" navigiert zur Asset-Lightbox (voller Modus) des Source-Bilds
- [ ] Fotos und Edits sind von diesem Modus **unberührt** — weiterhin voller Funktionsumfang
  (Caption, Tags, Gesichter-Zuweisung, Beziehungen, Metadaten)

---

## Checkliste

### Backend

- [ ] `GET /api/faces/{id}` neu: liefert `FaceDetailDto` (Kontrakt siehe README) —
  `versions` per `SELECT * FROM version WHERE face_id = :id`, `source_asset_id = face.asset_id`
- [ ] Prüfen ob `PATCH /api/faces/{id}` für Favorit/Löschen gebraucht wird oder bestehende
  Endpunkte (`api/faces.py`) reichen — 🟡 kurz verifizieren, nicht neu bauen falls vorhanden

### Frontend — Lightbox-Modus

- [ ] `LightboxTarget = { kind: 'asset'; assetId: number } | { kind: 'face'; faceId: number }`
  (oder Signal-Paar) als neuer Input/Store-State statt bisher nur `assetId`
- [ ] `detail = computed(...)` lädt je nach `kind` `AssetDetailDto` oder `FaceDetailDto`
- [ ] Template-Sektionen (Caption/Tags/Gesichter) hinter `@if (target().kind === 'asset')`
- [ ] Versionen-Sektion (aus Phase 4) bekommt generische Quelle: `detail().versions` funktioniert
  für beide DTOs unverändert, wenn beide `versions: VersionDto[]` liefern
- [ ] Neue Zeile „Quelle" im Face-Modus: Thumbnail + Klick → `openLightbox({ assetId: sourceAssetId })`
- [ ] `gallery.effects.ts` `openFaceLightbox$`: `faceId` durchreichen statt zu verwerfen

### Store / Actions

- [ ] `galleryActions.openFaceLightbox` Payload bleibt `{ faceId, assetId }`, aber Lightbox
  öffnet jetzt im Face-Modus auf `faceId` (bisheriges Verhalten war ein Workaround)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
