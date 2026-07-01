# Phase 5 — Beziehungen-Sektion + RelationBrowser-Modal

**Tier:** standard
**Status:** complete

Setzt Phase 1 voraus (`original_id`, `linked_edits[]` im Detail-DTO).

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/lightbox/lightbox.html` — kein Beziehungen-Block
- `frontend/src/app/services/asset.service.ts` — `setAssetOriginal()`, `patchAsset()` (Phase 1)
- `docs/design/js/detail.jsx` — Beziehungen-Sektion (ab ca. Zeile ~407)
- `docs/design/js/relation.jsx` — `RelationBrowser`-Komponente (vollständig)

---

## Abnahme-Kriterien

- [x] Sektion „Beziehungen" nach der Versionen-Sektion sichtbar
- [x] Untersektion „Originalvorlage": zeigt Thumbnail-Zeile wenn `original_id` gesetzt, sonst „Original zuordnen"-Button
- [x] Thumbnail-Zeile: kleines Thumbnail + `#ID` + „Original"-Badge + Bearbeiten (Picker öffnen) + Entfernen
- [x] Untersektion „Verknüpfte Edits · N": listet alle `linked_edits` mit Thumbnail + Source-Badge + Entfernen
- [x] „Edit verknüpfen"-Button öffnet RelationBrowser-Modal
- [x] RelationBrowser: Vollbild-Modal mit Textsuche + Bild-Grid (Auswahl per Klick)
- [x] Bestätigen im RelationBrowser setzt `original_id` per `patchAsset()` + Reload
- [x] Zuordnung entfernen (X-Button) ruft `patchAsset(editId, { original_id: null })`
- [x] RelationBrowser-Modal liegt über Lightbox (z-index korrekt)

---

## Checkliste

### Beziehungen-Template

- [x] Sektion nach Versionen einfügen:
  ```html
  <div class="panel-sec">
    <div class="psec-title">Beziehungen</div>

    <!-- Originalvorlage -->
    <div class="rel-dir-lbl">Originalvorlage</div>
    @if (detail()?.original_id != null) {
      <div class="rel-row">
        <div class="rr-thumb"><img [src]="originalThumbnailUrl()" /></div>
        <div class="rr-body">
          <div class="rr-id">#{{ detail()!.original_id }} <span class="rel-tag rel-tag--orig">Original</span></div>
        </div>
        <button class="iconbtn" (click)="openRelationBrowser('origin')"><pf-icon name="pencil" /></button>
        <button class="rr-x" (click)="removeOriginal()"><pf-icon name="x" /></button>
      </div>
    } @else {
      <button class="rel-add" (click)="openRelationBrowser('origin')">
        <pf-icon name="link" /> Original zuordnen
      </button>
    }

    <!-- Verknüpfte Edits -->
    <div class="rel-dir-lbl rel-dir-lbl--spaced">
      Verknüpfte Edits · {{ detail()?.linked_edits?.length ?? 0 }}
    </div>
    @for (edit of detail()?.linked_edits ?? []; track edit.id) {
      <div class="rel-row">
        <div class="rr-thumb"><img [src]="editThumbnailUrl(edit)" /></div>
        <div class="rr-body">
          <div class="rr-id">#{{ edit.id }} <span class="rel-tag rel-tag--edit">{{ sourceLabel(edit.source) }}</span></div>
        </div>
        <button class="rr-x" (click)="removeEditLink(edit.id)"><pf-icon name="x" /></button>
      </div>
    }
    <button class="rel-add" (click)="openRelationBrowser('edits')">
      <pf-icon name="plus" /> Edit verknüpfen
    </button>
  </div>
  ```
- [x] `originalThumbnailUrl()`: über `assetService.thumbnailUrl(id, 256)` (`size=64` ist kein gültiger Wert im typisierten Service — 256 passt zum Rest der App, siehe Report-Back)
- [x] `editThumbnailUrl(edit)`: dito
- [x] `removeOriginal()`: `patchAsset(asset.id, { original_id: null })` + reload
- [x] `removeEditLink(editId)`: `patchAsset(editId, { original_id: null })` + reload

### RelationBrowser-Modal

- [x] `showRelationBrowser = signal<'origin' | 'edits' | null>(null)`
- [x] `openRelationBrowser(mode)` setzt Signal
- [x] Modal außerhalb `.lb` (korrekte z-index-Ebene):
  ```html
  @if (showRelationBrowser()) {
    <div class="rb-scrim" (click)="closeRelationBrowser()">
      <div class="rb-modal" (click)="$event.stopPropagation()">
        <!-- Kopf: Titel + Schließen -->
        <!-- Suchfeld -->
        <!-- Bild-Grid: alle Assets, ausgenommen aktuelles -->
        <!-- Footer: Ausgewählt-Anzeige + Abbrechen + Bestätigen -->
      </div>
    </div>
  }
  ```
- [x] Bild-Grid lädt aus `assetService.listAssets()` (eigene Ladung statt Gallery-Store — der Store hält nur die aktuell gefilterte Galerie-Ansicht, nicht zwingend alle Assets; MVP: erste 200, sortiert nach Datum)
- [x] Suche filtert clientseitig auf `id`, `source` (kein `caption`-Feld auf `AssetDto` vorhanden — siehe Report-Back)
- [x] Einfach-Auswahl für „origin" (ein Original), Multi-Auswahl für „edits" (mehrere Edits)
- [x] Bestätigen:
  - origin: `patchAsset(asset.id, { original_id: selectedId })` + reload
  - edits: diff zu `linked_edits` → neue: `patchAsset(editId, { original_id: asset.id })`; entfernte: `patchAsset(editId, { original_id: null })`
- [x] SCSS: `.rb-scrim`, `.rb-modal`, `.rb-grid`, `.rb-cell`, `.rb-head`, `.rb-foot`

---

## Report-Back

- Thumbnail-Größe: Plan-Skizze nannte `size=64`, der typisierte `assetService.thumbnailUrl()` erlaubt nur `256|512|1024` — 256 genutzt (kleinste erlaubte Stufe, konsistent mit dem Rest der App).
- Bild-Grid im RelationBrowser lädt selbstständig über `assetService.listAssets()` (200 neueste), nicht aus dem Gallery-Store — der Store spiegelt nur die aktuell gefilterte Galerie-Ansicht, das wäre für "alle Assets durchsuchen" falsch gewesen.
- Suche filtert auf `#ID` + Quelle. Caption steht nicht auf `AssetDto` (nur auf `AssetDetailDto`) — Caption-Suche im MVP ausgelassen, wie im Plan als "ggf." vorgesehen.
- Auswahl per Einzelklick (Toggle) + Bestätigen-Button statt Doppelklick-Sofortbestätigung — konsistent mit Multi-Auswahl bei Edits, ein einheitliches Interaktionsmuster für beide Modi.
- Design-Mockup (`relation.jsx`) hat zusätzlich Personen-/Quelle-/Framing-Facetten-Filter und eine mobile Filter-Sheet-UI — laut Plan-Checkliste (🟡-Notiz) ist das MVP mit reiner Textsuche für Phase 5 ausreichend; Facetten-Filter wären ein Follow-up, falls die Liste unhandlich wird.
