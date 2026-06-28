# Phase 4 — Versionen-Sektion + VersionCompare-Modal

**Tier:** standard
**Status:** pending

Setzt Phase 1 voraus (`versions: VersionDto[]` im Detail-DTO).

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/lightbox/lightbox.html` — Stub `<!-- Stub: Versionen -->`
- `frontend/src/app/models/asset.model.ts` — `VersionDto`
- `docs/design/js/detail.jsx` — Versionen-Sektion (ab ca. Zeile ~379) + `openNewVersion`
- `docs/design/js/compare.jsx` — `VersionCompare` + `ComparePanel` + `buildItems()`

---

## Abnahme-Kriterien

- [ ] Versionen-Sektion zeigt alle `detail().versions` als Liste
- [ ] Jede Zeile: Thumbnail + Label + „Aktiv"-Badge (wenn `is_current`) + Datum + Params (wenn vorhanden)
- [ ] Aktive Version ist visuell hervorgehoben
- [ ] „Vergleichen"-Link in Sektion-Header → öffnet VersionCompare-Modal
- [ ] VersionCompare-Modal: Side-by-Side, jede Seite hat Panel-Selektor (Tabs)
- [ ] Panel-Selektor enthält: aktuelle Ansicht + alle Versionen + verlinktes Original + verknüpfte Edits
- [ ] Footer jeder Seite: Auflösung + Quelle + Datum
- [ ] Overlay schließt per Klick auf Scrim oder X-Button
- [ ] „Neue Version ergänzen"-Button vorhanden (Drag-Drop für spätere Umsetzung; vorerst nur visuell)

---

## Checkliste

### Versionen-Liste

- [ ] Stub-Kommentar ersetzen durch echte Sektion:
  ```html
  <div class="panel-sec">
    <div class="psec-title psec-title--row">
      Versionen · {{ detail()?.versions?.length ?? 0 }}
      <button class="psec-act" (click)="openVersionCompare()">Vergleichen</button>
    </div>
    <div class="vers">
      @for (version of detail()?.versions ?? []; track version.id) {
        <div class="vrow" [class.vrow--cur]="version.is_current">
          <div class="vthumb"><img [src]="version.thumbnail_url" /></div>
          <div class="vinfo">
            <div class="vname">
              {{ versionLabel(version) }}
              @if (version.is_current) { <span class="vtag vtag--cur">Aktiv</span> }
            </div>
            <div class="vmeta">{{ versionMeta(version) }}</div>
          </div>
        </div>
      }
    </div>
    <button class="lb-newver">
      <pf-icon name="upload" [size]="16" />
      <div>
        <div class="nv-t">Neue Version ergänzen</div>
        <div class="nv-s">Edit hierher ziehen oder klicken</div>
      </div>
    </button>
  </div>
  ```
- [ ] `versionLabel(v: VersionDto): string` — `v.type ?? 'Version'` + Fallback-Logik
- [ ] `versionMeta(v: VersionDto): string` — Auflösung + Datum + ggf. Strength/Modell aus `params`

### VersionCompare-Modal

- [ ] Neue Signal-Komponente oder Inline-Modal: `showVersionCompare = signal(false)`
- [ ] `openVersionCompare()` in `lightbox.ts`
- [ ] `compareItems = computed(...)` — baut Liste nach Mockup-`buildItems()`:
  1. Aktuelles Asset (tag: 'current')
  2. Jede Version (tag: 'version')
  3. Verlinktes Original wenn `detail().original_id` gesetzt (tag: 'original')
  4. Verknüpfte Edits aus `detail().linked_edits` (tag: 'edit')
- [ ] Modal-Template außerhalb `.lb` (Scrim-Ebene analog zu PersonPicker):
  ```html
  @if (showVersionCompare()) {
    <div class="vc-scrim" (click)="closeVersionCompare()">
      <div class="vc-modal" (click)="$event.stopPropagation()">
        <div class="vc-head">...</div>
        <div class="vc-panels">
          <!-- Linke Seite -->
          <div class="vc-panel">
            <div class="vc-panel-sel">
              @for (item of compareItems(); ...) {
                <button [class.on]="leftIdx() === i" (click)="setLeftIdx(i)">{{ item.label }}</button>
              }
            </div>
            <div class="vc-img-wrap"><img [src]="compareItems()[leftIdx()].thumbnailUrl" /></div>
            <div class="vc-panel-foot">...</div>
          </div>
          <div class="vc-divider"></div>
          <!-- Rechte Seite (analog) -->
        </div>
      </div>
    </div>
  }
  ```
- [ ] `leftIdx = signal(0)`, `rightIdx = signal(1)` (Default: aktuell links, erste Version rechts)
- [ ] `compareItemImageUrl(item)`: `/api/assets/{id}/file` für Asset-Items, `version.thumbnail_url` für Versionen
- [ ] SCSS: `.vc-scrim`, `.vc-modal`, `.vc-panels`, `.vc-panel`, `.vc-panel-sel`, `.vc-panel-foot`, `.vc-divider`, `.vc-tag`

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
