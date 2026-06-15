# Handoff: Photofant — Galerie-App

## Übersicht

Photofant ist eine **lokal laufende Foto-Verwaltungs-App** für KI-generierte und fotografische Assets. Der Fokus liegt auf:

- Einer justierten Bildergalerie mit Filter-Rail und 3-stufiger Suche
- Personen-Erkennung und -Verwaltung (Face-Embedding)
- Automatischem Tagging, Captioning und semantischer Suche
- Modell-Verwaltung (lokale ONNX-Modelle)
- Einem integrierten Bild-Editor

**Slogan:** „vergisst nie"

---

## Über die Design-Dateien

Die Dateien in diesem Paket sind **HTML-Prototypen**, keine Produktions-Codebasis. Sie zeigen das beabsichtigte Aussehen und Verhalten der App. Die Aufgabe ist es, diese Designs in der Ziel-Technologie des Projekts zu implementieren — **Angular + Tailwind + NgRx** (siehe `docs/PROJECT.md`; die Prototypen selbst sind in React-JSX gebaut, das ist nur Prototyp-Vehikel). Nutze die HTML-Prototypen als visuelle und verhaltenstechnische Referenz, übertrage aber keine Browser- oder React-spezifischen Lösungen direkt.

**Fidelity:** High-fidelity. Die Prototypen haben finales Farbsystem, finale Typografie, fertige Spacing-Tokens und funktionierende Interaktionen. Pixel-genaue Reproduktion ist das Ziel.

---

## Screens / Views

### 1. App-Shell

**Layout:**
- 2-Spalten-Grid: `var(--nav-w): 212px` Links-Rail + `1fr` Hauptbereich
- Breakpoint bei `860px`: Nav-Rail wird zur Slide-in-Drawer (translateX), untere Tab-Bar erscheint
- Top-Bar: `58px` Höhe, `border-bottom: 1px solid var(--line)`

**Nav-Rail (`.nav`):**
- Hintergrund: `var(--bg)` = `oklch(0.165 0.006 256)`
- Padding: `14px 10px`, Gap: `2px`
- Brand-Mark: 28×28px, border-radius 8px, blauer Radial-Gradient
- Markenname: Helvetica Neue, 15px, font-weight 700
- Nav-Items (`.nav-item`): Flex row, gap 11px, padding 8px 10px, radius 7px
  - Aktiv: `background: var(--accent-weak)`, Icon-Farbe: `var(--accent)`
  - Hover: `background: var(--surface)`
  - Count-Badge: rechts, 11px, `font-family: var(--mono)`, Farbe `var(--text-3)`
- Gruppen-Label: 10px, letter-spacing 0.14em, uppercase, `var(--text-3)`
- Spacer-Bereich: Storage-Indicator am unteren Rail-Ende
  - Fortschrittsbalken: 5px, Gradient von `var(--accent)` nach `oklch(0.62 0.15 285)`

**Top-Bar (`.top`):**
- Filter-Button (links, `iconbtn`), Titel, Search-Box (mittig, flex:1), Actions (rechts)
- Actions: Import-Button, Duplikat-Scan-Icon, Shortcuts-Icon, Job-Pill

**Job-Pill (`.jobpill`):**
- Standardzustand: `background: var(--surface)`, border: 1px solid `var(--line)`
- Aktiv (Jobs laufen): border-color `var(--accent-line)`, Spinner-Icon
- Spinner: 14×14px circle, `border-top-color: var(--accent)`, animation 0.8s linear

---

### 2. Galerie-View

**Filter-Rail (`.rail`):**
- Breite: `264px` (Breakpoint 1080px: 248px)
- Facetten: Person, Quelle, Framing, Qualität, Sammlung, Tags
- Jede Facette hat einen chevron-gesteuerten Accordion-Toggle
- Checkbox-Rows (`.frow`): hover → `var(--surface)`, aktiv → `.on` Klasse, Checkbox 16×16px, radius 5px
- Qualitäts-Slider: Custom-Drag-Implementierung, Range 0–1, Knob 15×15px
- Tag-Suche: Eingabefeld mit Icon, 32px Höhe

**Sub-Toolbar (`.subbar`):**
- Sticky oben, backdrop-blur(10px), Hintergrund 82% Opazität
- Links: Ergebnis-Count + aktive Filter-Chips
- Rechts: Grupperungs-Segmentcontrol (Monat/Person/Quelle), Sort-Button, Dichte-Control, Auswählen-Button
- Filter-Chips (`.chip`): height 28px, padding `0 6px 0 11px`, radius 8px, `var(--surface)`, border `var(--line)`
  - Aktive Kategorie-Chips: `.accent` → `var(--accent-weak)` bg, `var(--accent-line)` border

**Foto-Grid (`.grid`):**
- `display: flex; flex-wrap: wrap` — justiertes (Brick-Layout) Raster
- Jede Zelle: `flex-grow: ar.w / ar.h`, `flex-basis: base * ar.w/ar.h px`
- Base-Höhe je Dichte: sm=150px, md=196px, lg=250px (Desktop); sm=96, md=122, lg=150 (Mobile)
- Gap: 8px (Desktop), 6px (Mobile)
- Gruppiert nach Monat/Person/Quelle mit Monats-Header

**Grid-Zelle (`.cell`):**
- border-radius: `var(--radius)` = 10px, overflow hidden, cursor pointer
- Hover: `translateY(-1px)`, Veil-Overlay (Gradient) fade in
- Selektiert (`.sel`): `outline: 3px solid var(--accent)`, inner Image scale(0.93)
- Hover-Elemente: Pick-Circle (top-left, 22px), Fav-Stern (top-right, 26px), Meta-Badges (bottom-left), Version-Count (bottom-right)
- Pick-Circle: opacity 0 → 1 bei hover oder selmode, blauer Hintergrund wenn selektiert
- Fav-Stern: opacity 0 → 1 bei hover, permanent sichtbar wenn aktiv (`--gold`)
- Badges: 9.5px mono, uppercase, `background: rgba(0,0,0,.55)`, blur(4px)
  - FLUX: `oklch(0.55 0.16 285 / .85)`, SDXL: `oklch(0.52 0.13 200 / .85)`, Upscale: `oklch(0.50 0.13 152 / .85)`

---

### 3. Lightbox / Detail-Ansicht

**Overlay:**
- Scrim: `position: fixed; inset: 0`, `oklch(0.10 0.005 256 / .82)`, backdrop-blur(6px)
- 2-Spalten-Grid: `1fr 372px`

**Bild-Stage (links):**
- Zoom/Pan: Mausrad, Doppelklick, Touch-Pinch, Drag
- Max-Zoom: 6×, Zoom-Indikator-Pill unten-rechts
- Navigations-Buttons: 44×44px, border-radius 50%, links/rechts, backdrop-blur

**Detail-Panel (rechts, `.panel`):**
- Hintergrund: `var(--bg)`, border-left: 1px solid `var(--line)`
- Sektionen mit `padding: 16px 18px`, durch `border-bottom` getrennt
- Sections: Aktionen, Metadaten (KV-Grid), Caption, Tags, Gesichter, Versionen, Generation-Meta, Verwandte Assets

**KV-Grid (`.kv`):**
- `grid-template-columns: 92px 1fr`, gap `7px 10px`
- Keys: `var(--text-3)`, 12px; Values: `var(--mono)` 11.5px

**Tag-Chips (`.tg`):**
- height 26px, `0 5px 0 9px`, radius 7px, `var(--surface)`, border `var(--line)`
- Manuell (`.manual`): accent-border, Dot-Indikator

**Versionen-Timeline (`.vers`):**
- Flex-Column, gap 4px
- Jede Version: Thumbnail 42×42px + Name + Meta
- Aktuelle Version: `var(--accent-weak)` Hintergrund

**Gesichter-Strip (`.faces-strip`):**
- 58×58px Thumbnails, radius 9px
- Name darunter, 10.5px; Confidence-Score, `var(--good)` grün

**Action-Buttons (unten, `.pbtn-row`):**
- Zwei Buttons: Primary (Bearbeiten) = `var(--accent)` bg, Ghost (Download) = `var(--surface)`
- height 40px, radius 9px, font-weight 600

---

### 4. Personen-View

**Grid (`.people-grid`):**
- `grid-template-columns: repeat(auto-fill, minmax(150px, 1fr))`, gap 18px
- Jede Person-Card: Avatar 110×110px circle + Name + Meta

**Person-Card (`.person-card`):**
- Hover: Avatar scale(1.03) + ring `var(--accent-weak)`
- Doppelklick oder Long-Press → Inline-Namens-Editing
- Import-Button (upload icon) top-right, erscheint bei hover
- Drag-and-Drop: Dateien auf Karte ziehen → Import in Person-Ordner

**Inline-Namens-Editor:**
- Input, zentriert, 13.5px bold, `var(--surface-2)` bg, radius 7px
- Save (✓) / Cancel (✕) Buttons, je 24×24px

---

### 5. Alben-View

Zeigt kuratierte und Smart-Alben. Smart-Alben werden durch Trigger-Regeln automatisch befüllt (Personen, Tags, Captions). Toggle zwischen Smart/Manuell per Gear-Icon in der Album-Karte.

---

### 6. Review-Queue

**Layout:** Header (52px) + Body (Sidebar 216px + Main)
- Sidebar: Queue-Items mit Thumbnail + Name + Status
- Main: Großes Bild + rechts Aktionspanel
- Header: Progress-Bar (5px, `var(--accent)`), Fortschrittsanzeige mono

---

### 7. Modelle-View

**Tier-Gruppen:** Core, Optional, Generierung
- Jedes Modell: Karte mit Name, Beschreibung, Größe, Status-Badge
- Status-Badges: active (grün), available (blau), missing (rot), inplace (gelb)
- Inline-Drawer mit Details + Download/Bind-Aktionen
- Acquisition-Dialoge: Download-Dialog (Varianten-Auswahl + VRAM-Check), Bind-Dialog (Pfad-Auswahl)

---

### 8. Einstellungen

**6 Sektionen:** Bibliothek, Verarbeitung, Darstellung, Tastaturkürzel, Backup & Wartung, Info

**Komponenten:**
- `Switch`: Toggle-Pill, 42×24px, `var(--accent)` wenn aktiv
- `Row`: Title + optional Sub-Text + Steuerelement rechts
- `Group`: Grouped-List-Appearance (wie iOS Settings)
- `SliderRow`: Range-Input + Wert-Anzeige
- `PathRow`: Pfad-Anzeige mit Ändern-Button

---

### 9. Editor

Nimmt den vollen Viewport ein (kein App-Shell). Eigener State-Store (`editor-store.js`). Tools: Zuschneiden, Upscale, Flux-Edit, Farbkorrektur.

---

### 10. Duplikat-Check

Modal-Overlay mit Grid-Vergleich ähnlicher Bilder. Swipe/Click zum Markieren, dann Batch-Löschen.

---

## Interaktionen & Verhalten

### Navigation
- Desktop: Permanente Nav-Rail links (212px), Toggle via Filter-Button
- Mobile (≤860px): Slide-in-Drawer von links (268px), Scrim-Hintergrund, Bottom-Tab-Bar (60px)
- View-Routing: Purer Client-State (`view` string), kein Router nötig für MVP

### Galerie-Selektion
- Klick auf Zelle: Öffnet Lightbox (wenn kein selMode)
- Klick mit Cmd/Ctrl oder im selMode: Togglet Selektion
- Selektierte Zellen: outline + inneres Image-Scale-Animation
- Bulk-Bar erscheint wenn `sel.size > 0`: floating, centered, blur backdrop
  - Aktionen: Favorit, Taggen, Person zuweisen, Bearbeiten, Zu Trainingsset, Export, Papierkorb

### Lightbox-Navigation
- Prev/Next Buttons, Keyboard ← → Esc
- Alle Assets in der aktuellen gefilterten+sortierten Reihenfolge durchblätterbar
- Zoom: Mausrad (1.2× pro Step), Doppelklick (2.6×), Touch-Pinch, max 6×

### Suche (3 Modi)
- **Tags**: Filtert `asset.tags[].name.includes(query)`
- **Caption**: Filtert `asset.caption.toLowerCase().includes(query)`
- **Semantisch**: Loose-Match über caption + tags + scene-name
- Mode-Toggle: Pill-Buttons (Desktop) / Cycle-Button (Mobile)
- Autocomplete-Dropdown bei Focus mit modusabhängigen Vorschlägen

### Job-Dock
- Desktop: Popover unter Job-Pill-Button (340px breit)
- Mobile: Bottom-Sheet mit Scrim, Grabber, max-height 78vh
- Jobs animieren via `setInterval(700ms)` ihren Fortschritt

### Globales Drag & Drop
- Dateien auf beliebigen Bereich ziehen → Overlay-Pill + Import-Dialog öffnet sich

### Animationen
- Entrance-Animationen: `pop` (bulk bar, dialogs), `fade` (overlays), `pop2` (dock, modals)
- Easing: `ease` für fades, `cubic-bezier(.4,0,.2,1)` für Slide-Drawers
- Durations: 150–260ms
- `@media (prefers-reduced-motion: reduce)`: alle Durations auf 0.001ms

---

## State Management

```
App-State (useState):
  view: string                  // aktive View
  assets: Asset[]               // alle Assets (mutierbar: fav, tags, versions)
  F: Filters                    // { persons: Set, sources: Set, framings: Set, tags: Set, qualityMin: number, favOnly: bool, editedOnly: bool }
  search: { q: string, mode: "tags"|"caption"|"semantic" }
  sort: { key: "date"|"size", dir: "asc"|"desc" }
  group: "month"|"person"|"source"
  density: "sm"|"md"|"lg"
  sel: Set<id>                  // ausgewählte Asset-IDs
  selMode: boolean
  railOpen: boolean
  lb: { id, order: id[] } | null  // Lightbox
  dockOpen: boolean
  jobs: Job[]
  importCtx: object | null
  editAsset: Asset | null
  dupeCtx: object | null
  // Modal-States: mdDownload, mdBind, mdCaptioner
```

**Asset-Mutations:** Lokal via `setAssets(prev => prev.map(...))` — in Produktion durch API-Calls ersetzen.

---

## Design Tokens

### Farben

```css
/* Surfaces */
--bg:             oklch(0.165 0.006 256)   /* Haupt-Hintergrund */
--bg-2:           oklch(0.195 0.007 256)   /* Sekundär-Hintergrund, Grid-Bereich */
--surface:        oklch(0.225 0.008 256)   /* Karten, Inputs */
--surface-2:      oklch(0.255 0.009 256)   /* Erhöhte Elemente */
--surface-hover:  oklch(0.290 0.010 256)   /* Hover-Zustände */
--line:           oklch(0.305 0.010 256)   /* Trennlinien */
--line-2:         oklch(0.380 0.012 256)   /* Stärkere Trennlinien */

/* Text */
--text:   oklch(0.965 0.004 256)           /* Primär */
--text-2: oklch(0.760 0.010 256)           /* Sekundär */
--text-3: oklch(0.580 0.012 256)           /* Tertiär / Hints */

/* Akzente */
--accent:        oklch(0.685 0.135 248)    /* Primärer Blau-Akzent */
--accent-press:  oklch(0.620 0.135 248)    /* Gedrückt */
--accent-weak:   oklch(0.685 0.135 248 / 0.16)  /* Hintergrund-Tint */
--accent-line:   oklch(0.685 0.135 248 / 0.45)  /* Border-Tint */
--semantic:      oklch(0.700 0.150 305)    /* Semantische Suche (Lila) */
--gold:          oklch(0.820 0.130 86)     /* Favoriten-Stern */
--good:          oklch(0.740 0.130 152)    /* Erfolg / Grün */
--warn:          oklch(0.800 0.130 75)     /* Warnung / Gelb */
--danger:        oklch(0.660 0.165 25)     /* Fehler / Rot */
```

### Typografie

```
--font: "Helvetica Neue", Helvetica, Arial, system-ui, sans-serif
--mono: "IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace
```

Schriftgrößen-Skala (in px): 9, 9.5, 10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 15, 16

### Border-Radien

```
--radius:   10px   /* Standard (Karten, Inputs) */
--radius-s:  7px   /* Klein (Badges, Tags) */
--radius-l: 14px   /* Groß (Modals, Drawers) */
```

### Schatten

```
--shadow-1:   0 1px 2px rgba(0,0,0,.4)
--shadow-2:   0 6px 22px -6px rgba(0,0,0,.55)
--shadow-pop: 0 18px 48px -12px rgba(0,0,0,.7)
```

### Layout

```
--nav-w:   212px   /* Nav-Rail Breite */
--rail-w:  264px   /* Filter-Rail Breite */
--top-h:    58px   /* Top-Bar Höhe (54px auf Mobile) */
```

---

## Datenmodell

### Asset
```typescript
interface Asset {
  id: number;
  personId: number;          // -1 = unbekannt
  scene: number;             // visueller Szenen-Index
  source: "original" | "sdxl" | "flux";
  framing: "close_up" | "medium" | "full_body";
  ar: { w: number; h: number };   // Seitenverhältnis
  dims: { w: number; h: number }; // tatsächliche Pixel
  format: "jpeg" | "png";
  photo: string;             // URL (Thumbnail ~480px)
  photoLg: string;           // URL (Vollbild ~1100px)
  fileSize: number;          // KB
  quality: number;           // 0.0–1.0 (KI-Score)
  favourite: boolean;
  tags: { name: string; kind: "auto" | "manual" }[];
  caption: string;
  captioner: string;
  tagger: string;
  versions: Version[];
  versionCount: number;
  faces: Face[];
  date: Date;
  periodLabel: string;
  generationMeta: FluxMeta | SDXLMeta | null;
  bg: string;                // CSS-Gradient (Stand-in)
}

interface Version {
  type: "original" | "crop" | "upscale" | "flux_edit";
  label: string;
  current: boolean;
  res: string;               // z.B. "1024×1280"
  when: Date;
  params: object | null;
}

interface Face {
  personId: number;
  score: number;             // 0.0–1.0
  age: number;
  cropUrl: string;
}
```

### Person
```typescript
interface Person {
  id: number;
  name: string;
  count: number;             // Bilder in der Sammlung
  favCount: number;
  portrait: string;          // URL
  avatarBg: string;          // CSS-Gradient
}
```

### Collection (Album)
```typescript
interface Collection {
  id: string;
  name: string;
  desc: string;
  memberIds: number[];       // für manuelle Alben
  smart: {
    on: boolean;
    mode: "all" | "any";
    triggers: Trigger[];
  };
}
```

---

## Assets & Ressourcen

- **Schriften:** IBM Plex Mono von Google Fonts (weights 400, 500, 600). Helvetica Neue ist System-Font.
- **Icons:** Alle Icons sind custom SVGs, definiert in `js/icons.jsx` und via `window.Icon` als React-Komponente verfügbar. Jedes Icon ist eine Funktion die `{ name, size, fill, stroke, style }` akzeptiert.
- **Bilder:** Im Prototyp von `picsum.photos` (deterministische Seed-URLs). In Produktion durch echte Datei-Thumbnails aus dem lokalen Speicher ersetzen.
- **Portraits:** Im Prototyp von `randomuser.me`. In Produktion aus den extrahierten Gesichts-Embeddings.

---

## Datei-Übersicht

| Datei | Inhalt |
|---|---|
| `Photofant Galerie.html` | Haupt-Entry-Point, lädt alle Scripts |
| `styles.css` | Gesamtes Design-System, alle CSS-Tokens und Komponenten-Styles |
| `dialogs.css` | Styles für Import-Dialog und weitere Modale |
| `editor.css` | Styles für den Bild-Editor |
| `models.css` | Styles für die Modell-Verwaltung |
| `settings.css` | Styles für Einstellungen |
| `maintenance.css` | Styles für Wartungsbereich |
| `js/data.js` | Mock-Datenschicht, generiert Assets/Personen/Alben deterministisch |
| `js/icons.jsx` | Alle SVG-Icon-Definitionen |
| `js/components.jsx` | Shared UI-Primitives: `Img`, `Avatar` |
| `js/app.jsx` | App-Shell: Nav, Top-Bar, Search, Job-Dock, Bulk-Bar, Routing |
| `js/gallery.jsx` | Galerie-View: Filter-Rail, Grid, Zellen |
| `js/detail.jsx` | Lightbox / Detail-Ansicht mit Zoom/Pan |
| `js/albums.jsx` | Alben-View |
| `js/models.jsx` | Modell-Verwaltung |
| `js/models-dialogs.jsx` | Download- und Bind-Dialoge |
| `js/settings.jsx` | Einstellungen (6 Sektionen) |
| `js/maintenance.jsx` | Wartungsbereich |
| `js/review.jsx` | Review-Queue |
| `js/training.jsx` | Trainingssets-View |
| `js/import.jsx` | Import-Dialog |
| `js/relation.jsx` | Verwandte-Assets-Selektor |
| `js/editor.jsx` | Bild-Editor (Full-Screen) |
| `js/editor-store.js` | Editor State-Store |
| `js/editor-tools.jsx` | Editor Tool-Komponenten |
| `js/compare.jsx` | Duplikat-Checker |
| `js/dupecheck.jsx` | Duplikat-Logik |

---

## Implementierungshinweise

1. **Offline-First:** Die App ist konzeptuell vollständig lokal. Kein CDN für Assets, keine externen APIs außer für Modell-Downloads. Ideal für Electron/Tauri.

2. **Bildlader:** Der `Img`-Primitive rendert ein `<img loading="lazy">` mit Gradient-Hintergrund (aus `asset.bg`) als Ladeplatzhalter. In Produktion sollte der Gradient aus den dominanten Bildfarben generiert werden.

3. **Justiertes Grid:** Das Brick-Layout verwendet `display: flex; flex-wrap: wrap` mit `flex-grow: ar.w/ar.h`. Kein Masonry-CSS, kein JavaScript-Positioning — rein CSS-flex. Am Ende jeder Gruppe ein `flex-grow: 10` Spacer-Div.

4. **Semantische Suche:** Im Prototyp ein Fuzzy-Text-Match. In Produktion: CLIP/SigLIP-Embeddings für alle Assets vorberechnen, Query ebenfalls embedden, Cosine-Similarity ranking.

5. **Face-Pipeline:** InsightFace `buffalo_l` für Detection + Embedding. Clustering (ArcFace-Embeddings) für automatische Personen-Gruppierung. Matching-Schwelle: ~0.5 Cosine-Similarity.

6. **Model-Verwaltung:** VRAM-Check vor Download-Freigabe. Status-Enum: `active` (geladen), `inplace` (Pfad manuell gesetzt), `available` (herunterladbar), `missing` (fehlt).

7. **Responsive Breakpoints:**
   - `> 1080px`: Volle Desktop-Ansicht
   - `860px–1080px`: Kompaktere Filter-Rail (248px), engere Search-Box
   - `< 860px`: Mobile-Layout (Drawer-Nav, Bottom-Tab-Bar, Sheet-Dock)
   - `< 520px`: Kleinere Abstände, angepasste Lightbox-Aufteilung
