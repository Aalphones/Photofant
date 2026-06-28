# Phase 6 — Metadaten: editierbar + fehlende Felder

**Tier:** standard
**Status:** pending

Setzt Phase 1 voraus (`framing`, `quality` im Detail-DTO, `patchAsset()` in Service).

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/lightbox/lightbox.html` — Metadaten-Sektion ab Zeile ~133
- `frontend/src/app/features/galerie/lightbox/lightbox.ts` — `sourceLabel()`, Signals
- `docs/design/js/detail.jsx` — Metadaten-Sektion ab ca. Zeile ~428 (`<dl class="kv">`)
- `backend/photofant/api/assets.py` — `PATCH /api/assets/{id}` (Phase 1)

---

## Abnahme-Kriterien

- [ ] Quelle: editierbares Dropdown (original / flux / sdxl / …); Änderung wird per `patchAsset()` gespeichert
- [ ] Framing: editierbares Dropdown (Nahaufnahme / Halbkörper / Ganzkörper); Änderung wird gespeichert
- [ ] Seitenverhältnis sichtbar (read-only, aus width/height berechnet)
- [ ] Qualitätsscore sichtbar (read-only, farbig: ≥ 80 grün, ≥ 60 gelb, darunter gedimmt)
- [ ] Originalvorlage-Chip in Metadaten: kleines Thumbnail + `#ID` + Pencil → öffnet RelationBrowser (nutzt Phase-5-Logik)
- [ ] Alle geänderten Werte werden beim Navigieren zum nächsten Bild gespeichert (kein implizites Discard)

---

## Checkliste

### Fehlende Computed-Werte

- [ ] `aspectRatio = computed((): string => ...)`:
  - GGT von `width` und `height` berechnen → z.B. `16:9`, `3:4`
  - Hilfsfunktion `gcd(a, b)` (Euklidischer Algorithmus)
- [ ] `qualityDisplay = computed((): number | null => ...)`:
  - `Math.round((detail()?.quality ?? 0) * 100)` oder `null`
- [ ] `qualityClass = computed((): string => ...)`:
  - `q >= 80 → 'quality--good'`, `q >= 60 → 'quality--warn'`, sonst `'quality--low'`

### Editierbare Felder (Signals + Handler)

- [ ] `sourceDraft = signal<string | null>(null)` — gesetzt beim Öffnen der Lightbox
- [ ] `framingDraft = signal<string | null>(null)` — gesetzt beim Öffnen der Lightbox
- [ ] In Effect bei asset-Wechsel beide Drafts aus `asset()` initialisieren
- [ ] `onSourceChange(value: string)`: `sourceDraft.set(value)`, sofort `patchAsset({source: value})` + reload
- [ ] `onFramingChange(value: string)`: analog
- [ ] Kein separater „Speichern"-Button nötig — Dropdown `(change)` feuert direkt

### Template-Umbau Metadaten

- [ ] `<dl class="kv">` erweitern/umbauen:
  ```html
  <dt>Quelle</dt>
  <dd>
    <select class="kv-select" [value]="asset()?.source ?? ''" (change)="onSourceChange(...)">
      <option value="original">Original</option>
      <option value="flux">FLUX</option>
      <option value="sdxl">SDXL</option>
    </select>
  </dd>

  <dt>Originalvorlage</dt>
  <dd>
    @if (detail()?.original_id != null) {
      <span class="orig-chip">
        <img [src]="originalThumbnailUrl()" class="orig-thumb" />
        #{{ detail()!.original_id }}
        <button class="orig-edit" (click)="openRelationBrowser('origin')"><pf-icon name="pencil" [size]="11"/></button>
      </span>
    } @else {
      <button class="orig-link" (click)="openRelationBrowser('origin')">
        <pf-icon name="link" [size]="13"/> Zuordnen
      </button>
    }
  </dd>

  <dt>Framing</dt>
  <dd>
    <select class="kv-select" [value]="detail()?.framing ?? ''" (change)="onFramingChange(...)">
      <option value="">—</option>
      <option value="close_up">Nahaufnahme</option>
      <option value="medium">Halbkörper</option>
      <option value="full_body">Ganzkörper</option>
    </select>
  </dd>

  <dt>Auflösung</dt><dd>{{ dimensions() }}</dd>
  <dt>Seitenverhältnis</dt><dd>{{ aspectRatio() }}</dd>
  <dt>Format</dt><dd>{{ asset()?.format?.toUpperCase() ?? '—' }}</dd>
  <dt>Größe</dt><dd>{{ fileSize() }}</dd>
  <dt>Qualität</dt>
  <dd>
    @if (qualityDisplay() != null) {
      <span [class]="qualityClass()">{{ qualityDisplay() }} / 100</span>
    } @else { <span>—</span> }
  </dd>
  <dt>Hash</dt><dd class="kv-hash">{{ hashShort() }}</dd>
  ```
- [ ] Bestehende `<dt>Datum</dt>` entfernen (Datum steht bereits im Panel-Header)
- [ ] SCSS: `.kv-select` (inline, unstyled-like), `.orig-chip`, `.orig-thumb`, `.orig-edit`, `.orig-link`, `.quality--good`, `.quality--warn`, `.quality--low`

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
