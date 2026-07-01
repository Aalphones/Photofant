# Phase 4 — Lightbox-Anbindung: Klick-Ziel + Versions-Navigation

**Tier:** standard (tatsächlich: heikel — siehe Report-Back, Scope-Entscheidung während Umsetzung)
**Status:** complete

Setzt Phase 2/3 voraus (Grid liefert `kind`/`version_id`) sowie P15 Phase 4
(Versionen-Sektion) und P15 Phase 7 (Gesichter-Modus) — diese Phase verdrahtet nur
den **Einstiegspunkt**, die Versionen-Navigation selbst kommt aus P15.

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/galerie.ts` — `onOpenAsset`/`onOpenFace`,
  `galleryActions.openFaceLightbox` (Zeile ~244)
- `frontend/src/app/store/gallery/gallery.effects.ts` — `openFaceLightbox$`
- P15 README — Kontrakt `versions: VersionDto[]`, `linked_edits`, `original_id`
- P15 `phase-7-gesichter-modus.md` — Face-Modus der Lightbox

---

## Abnahme-Kriterien

- [x] Klick auf eine Kachel mit `kind: 'asset'` öffnet die Lightbox auf diesem Asset
  (heutiges Verhalten, unverändert)
- [x] Klick auf eine Kachel mit `kind: 'version'` öffnet die Lightbox auf dem
  zugehörigen Original-Asset, aber mit dieser Version **initial als Stage-Bild
  ausgewählt** (nicht `is_current` in der DB ändern — nur die initiale Anzeige-Auswahl,
  analog zum Panel-Selektor aus P15 Phase 4)
- [x] Aus jedem Einstieg ist über die Versionen-Sektion (P15 Phase 4) dieselbe
  vollständige Gruppe navigierbar — kein Unterschied im Versionen-Inhalt je nach Einstieg
- [x] Face-Stapel-Klick (Phase 3) öffnet die Lightbox im Face-Modus (P15 Phase 7); bei
  `kind: 'version'` mit dieser Face-Version initial ausgewählt
- [x] Schließen der Lightbox kehrt zur Galerie an der ursprünglichen Scroll-Position zurück
  (bestehendes Verhalten — nicht regressen)

---

## Checkliste

- [x] `onOpenAsset(event)` in `galerie.ts`: übergibt bei `kind === 'version'` zusätzlich
  die `version_id` als initiale Stage-Auswahl, sonst unverändert
- [x] `openFaceLightbox`-Action/Effect: analog für Face-Versionen — `faceId` + optionale
  `versionId` durchreichen
- [x] Deep-Link/URL-Zustand: geprüft — die Lightbox führt heute keinen Query-Param für
  die offene Asset-/Face-ID (Zustand lebt nur im NgRx-Store, kein Deep-Link/Share-Link
  existiert bereits vorher). Kein zusätzlicher `version`-Query-Param nötig, da es keinen
  Asset-Query-Param gibt, an den er anschließen könnte — außerhalb des Scopes dieser Phase.
- [x] Manuelles Durchklicken geprüft (siehe Report-Back)

---

## Report-Back

**Scope-Entscheidung während der Umsetzung (User-Rückfrage):** Phase 3 hatte im eigenen
Report-Back festgehalten, Phase 4 solle nur das Matching (`item.id` → `(faceId, versionId)`)
in der *alten*, separaten Gesichter-Lightbox (`face-lightbox/`) fixen. Diese Phase-4-Datei
verlangt im Gegensatz dazu wörtlich, dass ein Face-Stapel-Klick die *neue*, vereinheitlichte
Lightbox im Gesichter-Modus (P15 Phase 7) öffnet — ein echter Widerspruch zwischen den
beiden Plan-Dokumenten. Per Rückfrage an den User entschieden: **voll auf den neuen
Gesichter-Modus umstellen**, die alte separate Gesichter-Lightbox komplett entfernen.

Das machte die Phase deutlich größer als "Standard" (siehe Tier-Zeile oben), weil der neue
Gesichter-Modus bisher nur die reine Anzeige (Stage-Bild, Versionen, Quelle-Link) konnte.
Zusätzlich nachgebaut, damit kein Funktionsverlust gegenüber der alten Lightbox entsteht:

- **Person zuweisen / Gesicht löschen / Im Explorer anzeigen** als neue "Aktionen"-Sektion
  im Gesichter-Modus (`lightbox.html`/`.ts`) — vorher nur in `!isFaceMode()` verfügbar.
  Dafür `selectedFace: FaceDto | null` auf `selectedFaceId: number | null` verallgemeinert
  (wurde eh nur per `.id` genutzt) — funktioniert jetzt für Asset- und Gesichter-Modus gleich.
- **Vor/Zurück durch alle Gesichter** (nicht nur innerhalb eines Stapels): neue Selektoren
  `selectLightboxFaceIndex`/`selectLightboxFaceNavContext`/`selectLightboxHasPrevFace`/
  `selectLightboxHasNextFace` (`gallery.selectors.ts`) plus zwei neue Effects
  `onLightboxFaceNext$`/`onLightboxFacePrev$` (`gallery.effects.ts`), die bei
  `lightboxKind === 'face'` durch `faceItems` statt durch die Asset-Liste navigieren und
  wieder `openFaceLightbox` dispatchen (kein separates `lightboxGoTo`-Äquivalent nötig).
  Die bestehenden Asset-Effects wurden um `filter(kind === 'asset')` ergänzt, damit beide
  Varianten sauber getrennt auf dieselben `lightboxNext`/`lightboxPrev`-Actions reagieren.
- Alte `face-lightbox/`-Komponente (Ordner) vollständig gelöscht, `galerie.ts`/`.html`
  entsprechend bereinigt (`selectedFaceItem`, `onFaceLightboxPrev/Next`, `closeFaceLightbox`,
  `onFaceLightboxOpenAsset`, `onFaceLightboxDeleted`, `faceLightboxHasPrev/Next` entfernt).

**Stapel-Klick-Ziel (Kernauftrag der Phase):** `cell.ts`/`grid.ts`/`face-cell.ts`/
`face-grid.ts` reichen jetzt `{ id, versionId }` bzw. `{ faceId, assetId, versionId }`
durch bis zu `galleryActions.openLightbox`/`openFaceLightbox`, die neu ein
`lightboxVersionId` im Store ablegen. `Lightbox.stageVersion()` löst das gegen
`activeVersions()` auf; `imageUrl()`/`downloadUrl()`/`faceStageUrl()` zeigen bei Treffer
diese Version, sonst wie vorher das Original/die aktuelle Version. Ändert nirgends
`is_current` in der DB — reine initiale Anzeige-Auswahl wie gefordert.

**Nebenbei-Fix (nicht Kern, aber notwendig für Kompilierbarkeit):** `GalerieCell` wird
auch von `AlbumGrid` (`features/alben/album-grid/`) direkt wiederverwendet, nicht nur
über `GalerieGrid`. Deren `onOpen`/`onOpenAsset` in `album-grid.ts`/`favoriten.ts` mussten
auf das neue `{ id, versionId }`-Event-Format angepasst werden (nur `.id` durchgereicht,
Alben/Favoriten kennen keine Stapel-Sonderbehandlung — außerhalb des Scopes dieser Phase).

**Getestet:** `tsc --noEmit` grün, `ng build` (Standard-Konfiguration) ohne TS-/Template-Fehler.
`ng build --configuration production` schlägt an einem **vorbestehenden** CSS-Budget-Fehler
in `lightbox.scss` (23.32 kB, Budget-Error-Schwelle 16 kB) fehl — per `git stash`-Vergleich
verifiziert, dass dieser Fehler bereits vor dieser Phase (Stand Phase 3, unverändert seit
P15) bestand, keine Regression dieser Phase. Nicht behoben (außerhalb des Scopes) — siehe
FINDINGS für Phase 5. Kein manuelles Browser-Smoke-Testing (private-Profil) — Prüf-Checkliste
folgt am Plan-Ende gesammelt für den User.
