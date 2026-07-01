# Phase 3 — Frontend Gesichter-Grid: Stapel-Äquivalent

**Tier:** standard
**Status:** complete

Setzt Phase 1 voraus (Faces-Äquivalent der Stapel-Felder). Spiegelt Phase 2, aber
für `features/galerie/face-grid/` statt `grid/`.

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/face-grid/`, `face-cell/`
- `frontend/src/app/models/asset.model.ts` — `FaceGalleryItemDto`
- Phase 2 dieses Plans — gleiches Icon/gleiche SCSS-Klasse wiederverwenden, nicht neu erfinden

---

## Abnahme-Kriterien

- [x] Face-Zelle zeigt dasselbe Stapel-Icon wie Foto-Zelle (Phase 2), wenn `stack_size > 1`
- [x] Ein Face mit Edit-Version(en) zeigt **jede** Version als eigene Kachel (nicht nur
  die neueste) — Original-Face + jede Face-Version einzeln, je mit eigenem Datum
- [x] Wurde eine Face-Version zwischenzeitlich einer anderen Person zugewiesen, zeigt die
  Personensuche jede Kachel bei der Person, zu der sie aktuell physisch gehört (Original
  ggf. bei alter Person, Edit bei neuer — abhängig vom Phase-1-Befund zur Umhängung).
  Keine Frontend-Arbeit nötig: Backend filtert bereits pro `person_id` auf Face- und
  Version-Zeilen getrennt (`faces.py:list_faces_gallery`), Frontend zeigt nur an, was
  geliefert wird.

---

## Checkliste

- [x] `FaceGalleryItemDto` um `stack_size: number`, `stack_group_id: number | null` ergänzen
  — **Abweichung:** Backend liefert (Phase 1) tatsächlich auch `kind: 'face' | 'version'`
  und `version_id: number | null` für Faces (`faces.py:79-82`), entgegen der ursprünglichen
  Plan-Annahme "kein `kind`-Feld nötig". Beide Felder zusätzlich ergänzt, weil `version_id`
  für die Klick-Weiterleitung gebraucht wird (siehe unten) und `kind` 1:1 den Backend-Typ
  spiegelt.
- [x] `face-cell.ts`/`.html`: Stapel-Badge analog zu `cell` (Phase 2) einbauen — **Abweichung:**
  keine geteilte SCSS-Datei vorhanden (Angular View Encapsulation kapselt Component-Styles;
  `cell.scss` und `face-cell.scss` sind separate Dateien, kein gemeinsames Partial existiert).
  Gleiche Klasse **visuell** dupliziert (`face-cell__stack-badge`, identische Regeln,
  4px-Abstand statt 6px passend zum bestehenden `face-cell__badge`-Raster) statt einer
  nicht existierenden Datei "wiederverwendet" — Präzedenzfall: `face-cell__badge--upscaled`
  ist im selben Stil bereits pro Component dupliziert, nicht geteilt.
- [x] Sortierung im Face-Grid folgt dem eigenen Datum jedes Eintrags — unverändert, Backend
  liefert bereits korrekt sortierte Einträge (kein Frontend-Sort nötig)
- [x] Klick-Verhalten (`openFace`/`onOpenFace`) bleibt erhalten, liefert aber jetzt bei
  einem Version-Eintrag dessen `version_id` mit — Event-Typ in `face-cell`/`face-grid`
  auf `{ faceId, assetId, versionId }` erweitert. **Bewusst nicht angefasst:** die
  Matching-Logik in `galerie.ts` (`onOpenFace`/`onFaceLightboxPrev`/`onFaceLightboxNext`)
  sucht weiterhin nur nach `item.id`, ignoriert `versionId` — das ist laut README explizit
  Phase-4-Scope ("siehe Phase 4 für Lightbox-Seite"), siehe FINDINGS.
- [x] **Kritischer Fund während der Umsetzung** (nicht in der ursprünglichen Checkliste):
  `face-grid.html`s `@for`-Track lief auf `face.id` — Backend vergibt Version-Pseudo-
  Einträgen dieselbe `id` wie ihrem zugehörigen Face (`faces.py`: `id=face.id` in beiden
  Zweigen). Bei einem Stapel mit N Versionen hätten mehrere Grid-Einträge denselben
  Track-Key gehabt → Angular hätte DOM-Knoten zwischen Positionen falsch wiederverwendet,
  genau die Phase-3-AK "jede Version eine eigene Kachel" wäre in der Praxis brüchig
  gewesen (analog zum Entity-Key-Fund aus Phase 2). Behoben: Track-Funktion nutzt
  `versionId != null ? 'v'+versionId : 'f'+id`.

---

## Report-Back

Kleinerer Scope als Phase 2 — Backend hatte die Stapel-Felder für Faces bereits vollständig
in Phase 1 gebaut (`kind`/`version_id`/`stack_size`/`stack_group_id`, inkl. serverseitig
fertig aufgelöstem `thumbnail_url` für Version-Einträge). Frontend musste also **keine**
Thumbnail-URL-Auflösung nach `kind` bauen (anders als bei `AssetDto`/`cell.ts` in Phase 2)
— nur Badge + Track-Key + Event-Erweiterung.

**Getestet:** `tsc --noEmit` grün. Kein manuelles Smoke-Testing im Browser (private-Profil,
kein Playwright) — Prüf-Checkliste folgt am Plan-Ende gesammelt für den User.
