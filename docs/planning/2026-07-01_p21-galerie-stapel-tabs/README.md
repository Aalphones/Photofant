# P21 — Galerie: Stapel & Tab-Konsolidierung

**Status:** pending

Ziel: Die Galerie hat nur noch **zwei** Tabs (Fotos, Gesichter) statt aktuell drei
(`photos`/`faces`/`edits`). Edits verschwinden als eigener Tab und tauchen stattdessen
als **Stapel** unter ihrem Original auf — bei Fotos oder bei Gesichtern, je nachdem
was editiert wurde. Ein Edit kann physisch in einem anderen Personen-Ordner liegen
als sein Original (Person wurde beim Edit umgehängt); trotzdem gehören sie in der
Anzeige zusammen. Koordiniert sich mit P15 (Lightbox-Angleichung, insbesondere
Phase 4 Versionen-Sektion und Phase 7 Gesichter-Modus) und mit dem noch nicht
gestarteten P20 (Virtual-Scroll-Galerie) — beide fassen das Grid-Datenmodell an,
P20 sollte P21 **nach** dessen Abschluss aufsetzen (oder umgekehrt koordiniert
werden), nicht parallel im selben Query-Codepfad.

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

### Neues Konzept: „Stapel" (Edit-Gruppe)

Eine Stapel-Gruppe ist die Menge aller Bilder, die zu **einem** Original gehören:
das Original selbst + alle `version`-Zeilen seiner `asset_instance` + alle Assets
mit `original_id == asset.id`. Für Gesichter analog über `version.face_id`
(Gesichter haben keine `original_id`-Kette, nur die `version`-Tabelle).

- **`latest_activity_at`** = `max(created_at)` über alle Gruppenmitglieder
- **Stapel-Kopf-Eintrag**: Thumbnail + Sortierdatum = neuestes Gruppenmitglied;
  Klick öffnet die Lightbox auf genau diesem neuesten Mitglied
- **Original-Eintrag**: Thumbnail + Sortierdatum = `asset.created_at` (eigener
  Zeitpunkt); erscheint **zusätzlich**, nur wenn die Gruppe >1 Mitglied hat
  **und** das Original nicht selbst das neueste Mitglied ist (sonst wäre es
  identisch zum Stapel-Kopf → keine Dopplung)
- Beide Einträge zeigen ein Stapel-Icon, wenn die Gruppe >1 Mitglied hat; beide
  öffnen dieselbe Lightbox-Instanz, aus der heraus über die Versionen-Sektion
  (P15 Phase 4) zwischen allen Gruppenmitgliedern navigiert werden kann

🟡 **Zu verifizieren in Phase 1** (Chesterton's Fence, nicht annehmen): Folgt eine
`version`-Datei eines Edits automatisch dem Personen-Ordner, wenn das zugehörige
Face später einer anderen Person zugewiesen wird? Falls nicht, ist das ein
Vorfund, der eine eigene Korrektur braucht (nicht stillschweigend im Stapel-Query
mit-fixen).

### `AssetDto` (Galerie-Listenzeile) — neue Felder

```typescript
stack_size:      number        // 1 = kein Stapel; sonst Anzahl Gruppenmitglieder
list_role:       'solo' | 'stack_head' | 'original_echo'
effective_date:  string        // Sortierdatum dieses Eintrags (siehe oben)
thumbnail_source_id: number    // Asset- oder Version-ID, aus der das Thumbnail stammt
```

Gleiche vier Felder auf `FaceGalleryItemDto` (Gesichter-Tab), Gruppierung über
`version.face_id` statt `asset.original_id`.

### `GET /api/assets` (und `/api/faces`-Äquivalent) — Antwortsemantik

`total`/`page`/`items` zählen **Einträge** (nach Dual-Listing-Expansion), nicht
Assets — ein Original mit Edit kann für 2 Einträge sorgen. Diese Entscheidung
und ihre Kosten (Pagination-Zählung ist nicht mehr 1:1 zur Asset-Tabelle) stehen
in ADR-012 (Phase 5).

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
- [ ] Ein Original mit Edit(s) zeigt im Fotos-Tab einen Stapel: Thumbnail = neuestes
  Edit, Sortierdatum = Datum des neuesten Edits, Stapel-Icon unten rechts
- [ ] Dasselbe Original erscheint zusätzlich separat an seiner eigenen chronologischen
  Stelle (mit Stapel-Icon), sofern es nicht selbst das neueste Mitglied ist
- [ ] Klick auf den Stapel-Kopf öffnet die Lightbox auf dem neuesten Edit; Klick auf
  den separaten Original-Eintrag öffnet sie auf dem Original — beide navigierbar
  zu allen Versionen über die Versionen-Sektion
- [ ] Gleiches Verhalten im Gesichter-Tab (Face mit Edit-Version zeigt Stapel; Original-
  Face separat, ggf. unter anderer Person wenn umgehängt)
- [ ] Kein Datenverlust/keine Dopplung in Bulk-Operationen (Auswählen/Löschen/Favorisieren) —
  🟡 Phase 2/3 müssen prüfen, dass Dual-Listing nicht zu doppelten Bulk-Aktionen auf
  demselben Asset führt

---

## Archiv-Footer

**Summary:** —
**Files touched:** —
**Commits:** —
**Deviations:** —
**Follow-ups:** —
