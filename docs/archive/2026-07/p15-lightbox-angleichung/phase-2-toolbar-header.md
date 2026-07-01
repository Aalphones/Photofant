# Phase 2 — Stage-Toolbar + Panel-Header

**Tier:** standard
**Status:** complete

---

## Kontext (was vorher lesen)

- `frontend/src/app/features/galerie/lightbox/lightbox.html` — aktuelles Template
- `frontend/src/app/features/galerie/lightbox/lightbox.scss` — Styles
- `docs/design/js/detail.jsx` — Mockup: `lb-toolbar` (Stage), Panel-Header mit Avatar
- `docs/design/styles.css` — `.lb-toolbar`, `.lb-tool`, `.panel-sec.panel-header`

---

## Abnahme-Kriterien

- [x] Stage enthält Icon-Toolbar mit 4 Buttons (Favorit, Editor, Vergleichen, Download)
- [x] Favorit-Button zeigt Sternzustand (Farbwechsel `--gold` wenn aktiv — Icon-Komponente unterstützt kein SVG-Fill, gleiches Muster wie `.pbtn--fav-on`)
- [x] Panel-Header zeigt Avatar des ersten Gesichts (Portrait-Thumbnail) + Personenname
- [x] Wenn kein Gesicht: Fallback auf Person-Initiale oder Unbekannt-Platzhalter
- [x] Datum/Uhrzeit im Header (zwei Zeilen: Name / Datum)
- [x] Text-Button-Sektion „Aktionen" im Panel entfernen oder stark kürzen (Papierkorb bleibt separat)

---

## Checkliste

### Stage-Toolbar

- [x] `lb-toolbar` div im Stage einfügen (Mockup: absolute, oben rechts im Stage)
  ```html
  <div class="lb-toolbar">
    <button class="lb-tool" [class.lb-tool--on]="isFavourite()" ...>Stern</button>
    <button class="lb-tool" (click)="openEditor()">Crop</button>
    <button class="lb-tool" (click)="openVersionCompare()">Compare</button>
    <a class="lb-tool" [href]="downloadUrl()" download>Export</a>
  </div>
  ```
- [x] `openVersionCompare()` Signal + Handler anlegen (`showVersionCompare = signal(false)`) — reiner Stub, Modal-Inhalt folgt in Phase 4
- [x] `.lb-toolbar` + `.lb-tool` SCSS nach Mockup: positioniert, Icon-Größe, Hover-State

### Panel-Header umbauen

- [x] Ersten Gesicht-Avatar ermitteln:
  - `firstFace = computed(() => this.faces()[0] ?? null)`
  - Avatar-URL: direkt `face.crop_url` statt Person-`portrait_face_id`-Lookup — braucht keinen Store-Zugriff auf `personsSelectors.selectAll` und zeigt bildgenau das erkannte Gesicht (Deviation, siehe Report-Back)
- [x] Header-Template (Struktur wie geplant, Klassen `.ph-avatar`/`.ph-meta`/`.ph-name`/`.ph-date`/`.ph-fav`)
- [x] `firstPersonName()` computed: `faces()[0]?.person_name ?? '#' + asset()?.id`
- [x] SCSS für `.panel-header`, `.ph-avatar`, `.ph-meta` nach Mockup

### Aktionen-Sektion kürzen

- [x] Text-Buttons „Favorisieren" + „Bearbeiten" + „Herunterladen" entfernen (→ Toolbar)
- [x] Verbleibend im Panel (kein Pendant in Toolbar): Papierkorb, Klassifizieren, Upscale, **Im Explorer anzeigen** — „ComfyUI" gab es als Text-Button nie (nur eine tote `openComfyuiImportDialog()`-Methode ohne Template-Bindung, siehe Report-Back)
  - „Im Explorer anzeigen" wurde in Session 2026-06-28 ergänzt (ruft `POST /api/assets/{id}/reveal` auf, öffnet Explorer mit `/select,<pfad>`) — **blieb erhalten**
- [x] Diese restlichen Aktionen kompakter gestalten (Icon + kurzer Text, 2er-Grid) — war bereits 2er-Grid, jetzt ohne die drei ausgelagerten Buttons

---

## Report-Back

- Avatar-Quelle: statt Person-`portrait_face_id` (bräuchte geladene `personsSelectors.selectAll`) direkt `face.crop_url` des ersten erkannten Gesichts verwendet — einfacher, kein zusätzlicher Store-Zugriff nötig, zeigt exakt das auf diesem Bild erkannte Gesicht statt eines global gepflegten Personen-Portraits.
- Favorit-Zustand (Toolbar + Header-Icon) wird über Farbwechsel (`--gold`) signalisiert, nicht über einen gefüllten Stern — die `pf-icon`-Komponente rendert nur `stroke`, kein `fill`-Input vorhanden. Gleiches Muster wie das bestehende `.pbtn--fav-on`.
- „ComfyUI" aus der AK-Restliste in der Aktionen-Sektion existierte vorher nicht als sichtbarer Button — `openComfyuiImportDialog()` ist eine unbenutzte Methode ohne Template-Aufruf (Altlast, nicht Teil dieser Phase). Nicht angefasst, nur zur Kenntnis genommen.
- `openVersionCompare()` ist ein reiner Signal-Stub (`showVersionCompare`); das eigentliche Modal kommt in Phase 4.
