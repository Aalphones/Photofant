# P21 — Galerie: Stapel & Tab-Konsolidierung

**Status:** pending

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
Editor-Versionen (`version`-Tabelle) und separat angestoßene ComfyUI-Workflow-Imports
(eigene Assets über `original_id`) — beide zählen zur selben Gruppe, beide bekommen
eine eigene Galerie-Kachel. **Unterschiedliche Pipeline-Tiefe bleibt aber bestehen**
(Entscheidung 2026-07-01): ComfyUI-Workflow-Edits sind echte neue Bild-Dateien und
laufen komplett durch die normale Pipeline (eigene Faces/Captions/Tags — das gibt es
schon, keine neue Arbeit). Leichte Editor-Dialog-Edits (Crop/Rotate/Freistellen,
auch In-Place-ComfyUI über den Editor) bleiben bewusst **ohne** eigene Faces/Captions/
Tags — es ist dasselbe Foto, nur zugeschnitten/rotiert. Die Pipeline (Face-/Tag-/
Caption-Jobs, `processing_ledger`) wird in P21 **nicht** erweitert, um auch auf
`version`-Zeilen zu laufen.

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
| 1 | Backend: Stapel-Datenmodell & Query (Fotos + Gesichter) | heikel | pending |
| 2 | Frontend Galerie-Grid: Stapel-Icon + Tab-Konsolidierung | standard | pending |
| 3 | Frontend Gesichter-Grid: Stapel-Äquivalent | standard | pending |
| 4 | Lightbox-Anbindung: Klick-Ziel + Versions-Navigation | standard | pending |
| 5 | Doku & ADR-012 | mechanisch | pending |

---

## Abnahme-Kriterien (Gesamt)

- [ ] Sub-Toolbar zeigt nur noch „Alles / Fotos / Gesichter" — kein `edits`-Segment mehr
- [ ] Ein Original mit N Edits zeigt im Fotos-Tab N+1 einzelne Kacheln (Original + jedes
  Edit), jede an ihrer eigenen chronologischen Stelle, jede mit eigenem Thumbnail
- [ ] Alle Kacheln einer Gruppe zeigen das Stapel-Icon (unten rechts); Klick auf eine
  Kachel öffnet die Lightbox exakt auf dieser Version, navigierbar zu allen
  Geschwistern über die Versionen-Sektion
- [ ] Gleiches Verhalten im Gesichter-Tab (jede Face-Version eine eigene Kachel;
  Original-Face ggf. unter anderer Person als seine Edits, wenn umgehängt)
- [ ] Editor-Dialog-Edits (Crop/Rotate/Freistellen) bekommen weiterhin **keine** eigenen
  Faces/Captions/Tags; ComfyUI-Workflow-Edits behalten ihre bereits vorhandene volle
  Pipeline-Anbindung — keine Regression in beide Richtungen
- [ ] Kein Datenverlust/keine Dopplung in Bulk-Operationen (Auswählen/Löschen/Favorisieren) —
  jeder Eintrag ist ein eigenständiges physisches Objekt, Bulk-Aktionen wirken pro
  Eintrag, nicht pro Gruppe

---

## Archiv-Footer

**Summary:** —
**Files touched:** —
**Commits:** —
**Deviations:** —
**Follow-ups:** —
