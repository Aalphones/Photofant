# Phase 2 — Stage-Toolbar + Panel-Header

**Tier:** standard
**Status:** pending

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/lightbox/lightbox.html` — aktuelles Template
- `frontend/src/app/features/galerie/lightbox/lightbox.scss` — Styles
- `docs/design/js/detail.jsx` — Mockup: `lb-toolbar` (Stage), Panel-Header mit Avatar
- `docs/design/styles.css` — `.lb-toolbar`, `.lb-tool`, `.panel-sec.panel-header`

---

## Abnahme-Kriterien

- [ ] Stage enthält Icon-Toolbar mit 4 Buttons (Favorit, Editor, Vergleichen, Download)
- [ ] Favorit-Button zeigt Sternzustand (gefüllt wenn aktiv)
- [ ] Panel-Header zeigt Avatar des ersten Gesichts (Portrait-Thumbnail) + Personenname
- [ ] Wenn kein Gesicht: Fallback auf Person-Initiale oder Unbekannt-Platzhalter
- [ ] Datum/Uhrzeit im Header (zwei Zeilen: Name / Datum)
- [ ] Text-Button-Sektion „Aktionen" im Panel entfernen oder stark kürzen (Papierkorb bleibt separat)

---

## Checkliste

### Stage-Toolbar

- [ ] `lb-toolbar` div im Stage einfügen (Mockup: absolute, oben rechts im Stage)
  ```html
  <div class="lb-toolbar">
    <button class="lb-tool" [class.lb-tool--on]="isFavourite()" ...>Stern</button>
    <button class="lb-tool" (click)="openEditor()">Crop</button>
    <button class="lb-tool" (click)="openVersionCompare()">Compare</button>
    <a class="lb-tool" [href]="downloadUrl()" download>Export</a>
  </div>
  ```
- [ ] `openVersionCompare()` Signal + Handler anlegen (`showVersionCompare = signal(false)`)
- [ ] `.lb-toolbar` + `.lb-tool` SCSS nach Mockup: positioniert, Icon-Größe, Hover-State

### Panel-Header umbauen

- [ ] Ersten Gesicht-Avatar ermitteln:
  - `firstFace = computed(() => this.faces()[0] ?? null)`
  - Avatar-URL: `/api/faces/{face.id}/thumbnail` wenn `portrait_face_id` bekannt
- [ ] Header-Template:
  ```html
  <div class="panel-header">
    <div class="ph-avatar"><!-- img oder Initiale --></div>
    <div class="ph-meta">
      <div class="ph-name">{{ firstPersonName() }}</div>
      <div class="ph-date">{{ formattedDate() }}</div>
    </div>
    @if (isFavourite()) { <pf-icon name="star" .../> }
  </div>
  ```
- [ ] `firstPersonName()` computed: `faces()[0]?.person_name ?? '#' + asset()?.id`
- [ ] SCSS für `.panel-header`, `.ph-avatar`, `.ph-meta` nach Mockup

### Aktionen-Sektion kürzen

- [ ] Text-Buttons „Favorisieren" + „Bearbeiten" + „Herunterladen" entfernen (→ Toolbar)
- [ ] Verbleibend im Panel (kein Pendant in Toolbar): Papierkorb, Klassifizieren, ComfyUI, Upscale, **Im Explorer anzeigen**
  - „Im Explorer anzeigen" wurde in Session 2026-06-28 ergänzt (ruft `POST /api/assets/{id}/reveal` auf, öffnet Explorer mit `/select,<pfad>`) — **muss beim Umbau erhalten bleiben**
- [ ] Diese restlichen Aktionen kompakter gestalten (Icon + kurzer Text, 2er-Grid)

---

## Report-Back

_Hier trägt der Umsetzer nach Abschluss ein was abwich oder auffiel._
