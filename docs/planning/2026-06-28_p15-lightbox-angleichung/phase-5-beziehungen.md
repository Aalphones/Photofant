# Phase 5 — Beziehungen-Sektion + RelationBrowser-Modal

**Tier:** standard
**Status:** pending

Setzt Phase 1 voraus (`original_id`, `linked_edits[]` im Detail-DTO).

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/lightbox/lightbox.html` — kein Beziehungen-Block
- `frontend/src/app/services/asset.service.ts` — `setAssetOriginal()`, `patchAsset()` (Phase 1)
- `docs/design/js/detail.jsx` — Beziehungen-Sektion (ab ca. Zeile ~407)
- `docs/design/js/relation.jsx` — `RelationBrowser`-Komponente (vollständig)

---

## Abnahme-Kriterien

- [ ] Sektion „Beziehungen" nach der Versionen-Sektion sichtbar
- [ ] Untersektion „Originalvorlage": zeigt Thumbnail-Zeile wenn `original_id` gesetzt, sonst „Original zuordnen"-Button
- [ ] Thumbnail-Zeile: kleines Thumbnail + `#ID` + „Original"-Badge + Bearbeiten (Picker öffnen) + Entfernen
- [ ] Untersektion „Verknüpfte Edits · N": listet alle `linked_edits` mit Thumbnail + Source-Badge + Entfernen
- [ ] „Edit verknüpfen"-Button öffnet RelationBrowser-Modal
- [ ] RelationBrowser: Vollbild-Modal mit Textsuche + Bild-Grid (Auswahl per Klick/Doppelklick)
- [ ] Bestätigen im RelationBrowser setzt `original_id` per `patchAsset()` + Reload
- [ ] Zuordnung entfernen (X-Button) ruft `patchAsset(editId, { original_id: null })`
- [ ] RelationBrowser-Modal liegt über Lightbox (z-index korrekt)

---

## Checkliste

### Beziehungen-Template

- [ ] Sektion nach Versionen einfügen:
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
- [ ] `originalThumbnailUrl()`: `/api/assets/{original_id}/thumbnail?size=64`
- [ ] `editThumbnailUrl(edit)`: `/api/assets/{edit.id}/thumbnail?size=64`
- [ ] `removeOriginal()`: `patchAsset(asset.id, { original_id: null })` + reload
- [ ] `removeEditLink(editId)`: `patchAsset(editId, { original_id: null })` + reload

### RelationBrowser-Modal

- [ ] `showRelationBrowser = signal<'origin' | 'edits' | null>(null)`
- [ ] `openRelationBrowser(mode)` setzt Signal
- [ ] Modal außerhalb `.lb` (korrekte z-index-Ebene):
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
- [ ] Bild-Grid lädt aus `assetService.getAssets()` oder aus Gallery-Store (prüfen was am billigsten)
  🟡 RelationBrowser braucht alle Assets zum Durchsuchen. Wenn der Gallery-Store alle bereits hat:
  aus Store lesen. Sonst eigene Paginierung — MVP: ersten 200 laden reicht für Anfang.
- [ ] Suche filtert clientseitig auf `id`, `source`, ggf. Caption
- [ ] Einfach-Auswahl für „origin" (ein Original), Multi-Auswahl für „edits" (mehrere Edits)
- [ ] Bestätigen:
  - origin: `patchAsset(asset.id, { original_id: selectedId })` + reload
  - edits: diff zu `linked_edits` → neue: `patchAsset(editId, { original_id: asset.id })`; entfernte: `patchAsset(editId, { original_id: null })`
- [ ] SCSS: `.rb-scrim`, `.rb-modal`, `.rb-grid`, `.rb-cell`, `.rb-head`, `.rb-foot`

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
