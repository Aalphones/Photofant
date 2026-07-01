# P21 — Galerie: Stapel & Tab-Konsolidierung

**Status:** complete

Ziel: Die Galerie hat nur noch **zwei** Tabs (Fotos, Gesichter) statt aktuell drei
(`photos`/`faces`/`edits`). Edits verschwinden als eigener Tab. Stattdessen zeigt die
Galerie **jede Version einzeln** — das Original und jedes einzelne Edit bekommen je
eine eigene Kachel, an ihrer jeweils eigenen chronologischen Stelle, mit eigenem
Thumbnail. Ein Original mit 10 Edits erscheint also als 11 Kacheln, verstreut über
die Zeitleiste. Alle Kacheln einer Gruppe tragen ein Stapel-Icon und sind über die
Lightbox-Versionen-Sektion untereinander navigierbar. **Kein Kollabieren auf einen
bevorzugten „Kopf"-Eintrag** — jede Version ist gleichberechtigt sichtbar (Korrektur
2026-07-01: eine frühere Fassung dieses Plans hatte fälschlich nur 2 Einträge
[„Stapel-Kopf" + „Original"] vorgesehen).

Ein Edit kann physisch in einem anderen Personen-Ordner liegen als sein Original —
**bestätigt**, nicht nur Verdacht: editiert man ein Foto von Person X und die
Gesichtserkennung auf dem Edit erkennt Person Y, bleibt das Original bei Person X,
das Edit landet unter Person Y `edits/`. Eine Gruppe kann also über Personengrenzen
verteilt sein; Personen-Filter/-Suche zeigt jeweils nur die Mitglieder, die aktuell
zur gefilterten Person gehören (mit Stapel-Icon als Hinweis auf Geschwister anderswo).

Ein Original kann Edits aus **beiden** Mechanismen gleichzeitig haben — leichte
Editor-Versionen (`version`-Tabelle) und ComfyUI-Workflow-Imports (eigene Assets über
`original_id`) — beide zählen zur selben Gruppe, beide bekommen eine eigene Galerie-
Kachel. **Unterschiedliche Pipeline-Tiefe bleibt bestehen** (Entscheidung 2026-07-01):
ComfyUI-Workflow-Edits sind echte neue Bild-Dateien und laufen komplett durch die
normale Pipeline (eigene Faces/Captions/Tags). Leichte Editor-Dialog-Edits (Crop/Rotate/
Freistellen) bleiben bewusst **ohne** eigene Faces/Captions/Tags — es ist dasselbe Foto,
nur zugeschnitten/rotiert. Die Pipeline (Face-/Tag-/Caption-Jobs, `processing_ledger`)
wird in P21 **nicht** erweitert, um auch auf `version`-Zeilen zu laufen.

**Korrektur 2026-07-01 (Phase-1-Untersuchung):** Der ComfyUI-Default-Import
(Upscale/Edit/Inpaint, ADR-009) legte bislang immer eine `Version`-Zeile an, nie ein
eigenes Asset — die „das gibt es schon"-Annahme oben war falsch. Ohne eigenes Asset
läuft nie eine Gesichtserkennung auf dem Edit, also gab es die hier beschriebene
automatische Cross-Person-Wanderung nirgends. **ADR-013 löst das**: Phase 1 baut den
ComfyUI-Default-Import auf „legt eigenes Asset mit `original_id` an, volle Pipeline"
um (Ablösung des relevanten Teils von ADR-009) — erst danach ist die Umhänge-Logik
für ComfyUI-Edits real, nicht nur eine Annahme.

Koordiniert sich mit P15 (Lightbox-Angleichung, insbesondere Phase 4 Versionen-Sektion
und Phase 7 Gesichter-Modus) und mit dem noch nicht gestarteten P20 (Virtual-Scroll-
Galerie) — beide fassen das Grid-Datenmodell an, P20 sollte P21 **nach** dessen
Abschluss aufsetzen (oder umgekehrt koordiniert werden), nicht parallel im selben
Query-Codepfad.

---

## Ausgangslage (was heute existiert)

- **Zwei getrennte Edit-Mechanismen im Backend**, beide zählen für die Stapel-Logik:
  1. `version`-Tabelle — leichtgewichtige, nicht-destruktive Editor-Historie
     (Crop/Rotate/Rembg/ComfyUI-Ops) pro `asset_instance` **oder** `face`
     (XOR `instance_id`/`face_id`). Keine eigenen Tags/Captions/Faces.
  2. `asset.original_id` — vollwertiges neues Asset (eigener `content_hash`,
     durchläuft die volle Pipeline: Faces, Tags, Caption), erzeugt durch einen
     generativen ComfyUI-Run mit Auto-Import (ADR-008/009). Das ist bereits
     „Edit verhält sich wie Foto" — braucht **keine** neue Arbeit, nur eine
     andere Galerie-Darstellung.
- Aktuell existiert ein dritter Gallery-Tab `edits`, der **nur** Konzept 1 flach
  aus- listet (`VersionsPage`/`VersionGalleryItemDto`, `frontend/src/app/models/asset.model.ts:153`).
  Konzept 2 taucht heute im normalen `photos`-Tab als eigenständige Asset-Karte auf,
  ohne Bezug zum Original sichtbar zu machen.
- `GET /api/assets/{id}/thumbnail` (`backend/photofant/api/assets.py:379`) liefert
  immer die Datei des Assets selbst — nie die eines Edits. Ein Original mit neuerem
  Edit zeigt also heute ein veraltetes Thumbnail.
- `MEDIA_TYPES = ['photos', 'faces', 'edits']` (`frontend/src/app/models/asset.model.ts:4`)
  steuert den Sub-Toolbar-Umschalter (`features/galerie/sub-toolbar/`).

## Kontrakt (Backend → Frontend)

### Neues Konzept: „Stapel" (Edit-Gruppe) — flache Einzel-Einträge

Eine Stapel-Gruppe ist die Menge aller Bilder, die zu **einem** Original gehören:
das Original selbst + alle `version`-Zeilen seiner `asset_instance` + alle Assets
mit `original_id == asset.id`. Für Gesichter analog über `version.face_id`
(Gesichter haben keine `original_id`-Kette, nur die `version`-Tabelle).

- **Jedes Gruppenmitglied ist ein eigener, gleichberechtigter Galerie-Eintrag** —
  eigenes Thumbnail (sein eigenes Bild, nicht das der Gruppe), eigenes Sortierdatum
  (sein eigenes `created_at`). Kein Kollabieren, kein bevorzugter „Kopf"
- **`stack_size`** = Anzahl Mitglieder der Gruppe (1 = kein Stapel, kein Icon)
- **`stack_group_id`** = stabile ID der Gruppe (z.B. `id` des Originals) — identisch
  für alle Mitglieder derselben Gruppe; UI nutzt sie fürs Stapel-Icon/Tooltip
  („Stapel · N Versionen"), nicht für Aggregation
- Jeder Eintrag mit `stack_size > 1` zeigt das Stapel-Icon; Klick öffnet die Lightbox
  **auf genau diesem Eintrag** (nicht auf einem anderen Gruppenmitglied), von dort
  über die Versionen-Sektion (P15 Phase 4) zu allen Geschwistern navigierbar
- Gruppenzugehörigkeit ist **unabhängig von der aktuellen Person** — ein Edit, das
  zu Person Y umgehängt wurde, bleibt trotzdem Mitglied der Gruppe seines Originals
  bei Person X; nur die *Sichtbarkeit* pro Personen-Filter richtet sich nach der
  aktuellen Person des jeweiligen Eintrags

**Bestätigt in Phase 1 zu bauen/verifizieren** (Chesterton's Fence — erst verstehen,
was heute existiert, dann ergänzen): Ein Edit kann zu einer anderen Person wandern,
wenn die Gesichtserkennung auf dem editierten Bild eine andere Person erkennt. Für
originale Fotos gibt es dafür bereits die „Multi-Instanz-Semantik" (P7 Phase 3,
`docs/models.md` → `asset_instance`). Ob dieselbe Umhänge-Logik heute schon für
`version`-Zeilen (Editor-Edits) und für `original_id`-Kind-Assets (ComfyUI-Edits)
greift, ist zu prüfen — falls nicht, ist das der eigentliche Kern von Phase 1, nicht
nur die Anzeige-Logik.

### `AssetDto` (Galerie-Listenzeile) — neue Felder

```typescript
stack_size:      number        // 1 = kein Stapel; sonst Anzahl Gruppenmitglieder
stack_group_id:  number | null // gemeinsame ID über alle Mitglieder einer Gruppe
```

Gleiche zwei Felder auf `FaceGalleryItemDto` (Gesichter-Tab), Gruppierung über
`version.face_id` statt `asset.original_id`.

### `GET /api/assets` (und `/api/faces`-Äquivalent) — Antwortsemantik

`total`/`page`/`items` zählen weiterhin **1:1 wie heute** — jedes physische Bild
(Original, jede `version`-Zeile, jedes `original_id`-Kind-Asset) ist genau ein Eintrag.
Kein Expansions-/Dual-Listing-Schritt mehr nötig — das vereinfacht Phase 1 gegenüber
der ursprünglichen Fassung dieses Plans erheblich. Die einzige neue Arbeit ist: auch
`version`-Zeilen und `original_id`-Kind-Assets müssen als vollwertige Zeilen in der
Fotos-Galerie erscheinen (heute tun das nur `original_id`-Kind-Assets; `version`-Zeilen
stecken nur im separaten `edits`-Tab). Diese Entscheidung + Trade-offs stehen in
ADR-012 (Phase 5).

---

## Phasen-Übersicht

| Phase | Thema | Tier | Status |
|---|---|---|---|
| 1 | Backend: Stapel-Datenmodell & Query (Fotos + Gesichter) | heikel | complete |
| 2 | Frontend Galerie-Grid: Stapel-Icon + Tab-Konsolidierung | standard | complete |
| 3 | Frontend Gesichter-Grid: Stapel-Äquivalent | standard | complete |
| 4 | Lightbox-Anbindung: Klick-Ziel + Versions-Navigation | standard (real: heikel) | complete |
| 5 | Doku & ADR-012 | mechanisch | complete |

---

## Abnahme-Kriterien (Gesamt)

- [x] Sub-Toolbar zeigt nur noch „Alles / Fotos / Gesichter" — kein `edits`-Segment mehr
- [x] Ein Original mit N Edits zeigt im Fotos-Tab N+1 einzelne Kacheln (Original + jedes
  Edit), jede an ihrer eigenen chronologischen Stelle, jede mit eigenem Thumbnail
- [x] Alle Kacheln einer Gruppe zeigen das Stapel-Icon (unten rechts); Klick auf eine
  Kachel öffnet die Lightbox exakt auf dieser Version, navigierbar zu allen
  Geschwistern über die Versionen-Sektion
- [x] Gleiches Verhalten im Gesichter-Tab (jede Face-Version eine eigene Kachel;
  Original-Face ggf. unter anderer Person als seine Edits, wenn umgehängt)
- [x] Editor-Dialog-Edits (Crop/Rotate/Freistellen) bekommen weiterhin **keine** eigenen
  Faces/Captions/Tags; ComfyUI-Workflow-Edits behalten ihre bereits vorhandene volle
  Pipeline-Anbindung — keine Regression in beide Richtungen
- [x] Kein Datenverlust/keine Dopplung in Bulk-Operationen (Auswählen/Löschen/Favorisieren) —
  jeder Eintrag ist ein eigenständiges physisches Objekt, Bulk-Aktionen wirken pro
  Eintrag, nicht pro Gruppe (bekannte Einschränkung: Version-Pseudo-Einträge haben
  mangels Backend-Endpunkt bewusst kein eigenes Favorit/Löschen, siehe ADR-012)

---

## Archiv-Footer

**Summary:** Galerie zeigt jetzt nur noch zwei Tabs (Fotos, Gesichter) statt drei — der
separate Edits-Tab ist weg. Original und jedes einzelne Edit (Editor-Version wie
ComfyUI-Workflow-Edit) erscheinen stattdessen als eigene, gleichberechtigte Kachel an
ihrer eigenen chronologischen Stelle, mit Stapel-Icon + Lightbox-Versions-Navigation.
ADR-013 (ComfyUI-Default-Import legt jetzt ein eigenes Asset statt einer Version an) war
Voraussetzung, um die Cross-Person-Wanderung für ComfyUI-Edits real zu machen.

**Files touched:** Backend `api/assets.py`, `api/faces.py` (Stapel-Query, neue DTO-Felder
`kind`/`version_id`/`stack_size`/`stack_group_id`) · `api/comfyui.py` + Import-Pipeline
(ADR-013). Frontend `features/galerie/` (grid, cell, face-grid, sub-toolbar, lightbox,
gesichter-modus) · `store/gallery/gallery.reducer.ts` (Entity-Key-Fix) ·
`models/asset.model.ts`. Doku: `docs/decisions/012-*.md`, `docs/code-map.md`,
`docs/models.md`, `docs/routes.md`. `frontend/angular.json` (CSS-Budget).

**Commits:** `67b0c42` (Plan angelegt) · `524ab98` (Korrektur flache Einzeleinträge) ·
`895b765` (ADR-013, ComfyUI-Edit als Asset) · `08c7d42` (Phase 1, Backend-Query) ·
`dffc7df` (Phase 2, Fotos-Grid) · `491a88c` (Phase 3, Gesichter-Grid) · `7bc66f6`
(Phase 4, Lightbox + Gesichter-Modus) · Phase 5 (Doku/ADR-012, dieser Commit).

**Deviations:**
- Phase 1 deutlich größer als geplant: ADR-013 + Import-Pipeline-Umbau mussten erst
  gebaut werden, bevor der Query-Umbau überhaupt Sinn ergab (siehe Phase-1-Report-Back)
- Phase 4 auf Rückfrage voll auf den neuen Gesichter-Modus umgestellt statt nur die alte
  separate Gesichter-Lightbox zu fixen; alte `face-lightbox/`-Komponente entfernt
- Phase 5: `GET /api/faces` aus der ursprünglichen Formulierung existiert nicht — realer
  Endpunkt ist `GET /api/faces/gallery`, war davor komplett undokumentiert (kein P21-Bug)

**Follow-ups (kein P21-Scope, in ADR-012 dokumentiert):**
- Kein Backend-Endpunkt für Favorit/Löschen auf einer einzelnen `version`-Zeile — Version-
  Pseudo-Einträge haben deshalb kein eigenes Auswählen/Favorit-Icon
- Kein UI-Einstiegspunkt mehr, eine Editor-Version als ComfyUI-Workflow-Input zu binden
  (`versionSlotBindings` bleibt verdrahtet, wird aber nie mehr befüllt) — ersatzlos
  akzeptiert, da kein aktiver Anwendungsfall bekannt
- P20 (Virtual-Scroll-Galerie) sollte diesen Plan als abgeschlossen voraussetzen, nicht
  parallel im selben Query-Codepfad arbeiten
