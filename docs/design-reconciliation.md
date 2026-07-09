# Design-Reconciliation — Photofant

> Erzeugt in Phase 1 des Plans `docs/planning/2026-06-19_design-angleichung/`.
> **Quelle Soll:** `docs/design/js/*.jsx` + `docs/design/README.md`
> **Quelle Ist:** `frontend/src/app/**`
> Stand: 2026-06-19

---

## Übersichts-Tabelle

| View | Design-Status | Abweichungstyp | Schwergrade |
|---|---|---|---|
| App-Shell — Nav-Rail | vorhanden | Design-missachtet | MITTEL × 2, KLEIN × 2 |
| App-Shell — Top-Bar | vorhanden | Design-missachtet | KLEIN |
| App-Shell — Mobile Nav | vorhanden | Design-missachtet | MITTEL |
| App-Shell — Job-Dock | vorhanden | keine | — |
| App-Shell — Bulk-Bar | vorhanden | keine | — |
| Galerie — Filter-Rail | vorhanden | Design-missachtet | GROSS × 2 |
| Galerie — Sub-Toolbar | vorhanden | Design-missachtet | MITTEL, KLEIN |
| Galerie — Grid-Zelle | vorhanden | Design-missachtet | MITTEL |
| Lightbox / Detail | vorhanden | sauber-verschoben | KLEIN (P7/P8) |
| Personen | vorhanden | sauber-verschoben | — (P7) |
| Alben | vorhanden | keine | — |
| Trainingssets | vorhanden | sauber-verschoben | — (P10) |
| Review-Queue | vorhanden | sauber-verschoben | — (kein P aktiv) |
| Modelle | vorhanden | keine | — |
| Wartung | vorhanden | keine | — |
| Papierkorb | nur Nav-Slot im Prototyp | Design-Lücke-erfunden | KLEIN |
| Tags | nur Nav-Slot im Prototyp | Design-Lücke-erfunden | GROSS → Phase 3 |
| Einstellungen | vorhanden | Design-missachtet | GROSS → Phase 2 |
| Import-Dialog | vorhanden | keine | — |

**Abweichungstypen:**
- **Design-missachtet** — Mockup existiert, Implementierung weicht ab.
- **Design-Lücke-erfunden** — Kein Mockup vorhanden, Implementierung freihändig erfunden.
- **sauber-verschoben** — Bewusst zurückgestellt auf Backlog-Plan (P7, P8, P10 o.ä.).
- **keine** — Impl entspricht Design oder Abweichung ist trivial/beabsichtigt.

---

## Detailbefunde pro View

### App-Shell — Nav-Rail

**Design:** `docs/design/js/app.jsx:14-59`  
**Impl:** `frontend/src/app/shell/nav-rail/nav-rail.html`, `nav-rail.ts:29-43`

| # | Punkt | Schwere | Belege Soll → Ist |
|---|---|---|---|
| 1 | **Favoriten-Nav-Item fehlt.** Design hat Favoriten als eigenständigen Main-Eintrag mit Count-Badge. | MITTEL → behoben | `app.jsx:21` → `nav-rail.ts`: Favoriten-Item + `/favoriten`-Route + Stub-Komponente hinzugefügt (Phase 4). Vollansicht in P7. |
| 2 | **Review-Queue-Nav-Item fehlt.** Design listet Review-Queue unter Verwaltung. | MITTEL → behoben | `app.jsx:25` → `nav-rail.ts`: Review-Queue-Item + `/review`-Route + Stub-Komponente hinzugefügt (Phase 4). Feature-Implementierung folgt in eigenem Plan. |
| 3 | **Tags extra im Nav** (nicht im Design-Nav). Tags wurden per ADR-005 in Einstellungen integriert. | KLEIN → behoben | `nav-rail.ts:33` Tags-Item entfernt (Phase 4). |
| 4 | **Storage-Indikator statisch.** Design zeigt echte Werte (GB, Assets, %). | KLEIN → bewusst gelassen | Kein Backend-Endpunkt für Speichernutzungs-Daten vorhanden; Implementierung erfordert eigenen Plan. |

---

### App-Shell — Top-Bar

**Design:** `docs/design/js/app.jsx:437-457`  
**Impl:** `frontend/src/app/shell/top-bar/top-bar.html`

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Import-Button: Text fehlt.** Design zeigt `selectbtn` mit Icon + Text "Importieren". Impl hat nur `iconbtn` (Icon only). | KLEIN | `app.jsx:446-448` `React.createElement("button", { className: "selectbtn" }, Icon("upload"), "Importieren")` → `top-bar.html:4` `<button class="iconbtn">…</button>` |

*Hinweis:* Filter-Toggle ist in Sub-Toolbar (nicht Top-Bar wie im Design) — das ist eine bewusste IA-Entscheidung, die besser zur Galerie-Struktur passt. Kein Defekt.

---

### App-Shell — Mobile Nav (Bottom Tab Bar)

**Design:** `docs/design/js/app.jsx:282-297`  
**Impl:** `frontend/src/app/shell/shell.html:51-68`

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Tab-Auswahl abweichend.** Design: [Galerie, Personen, Favoriten, Mehr]. | MITTEL → behoben | `shell.html`: Tabs auf [Galerie, Personen, Favoriten, Mehr] umgestellt. "Mehr" öffnet die Nav-Rail (Phase 4). |

---

### Galerie — Filter-Rail

**Design:** `docs/design/js/gallery.jsx:24-83`  
**Impl:** `frontend/src/app/features/galerie/filter-rail/filter-rail.html`

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Person-Facette fehlt komplett.** Design hat Person-Facette als erste Facette mit Avatar-Chips. | GROSS → sauber-verschoben P7 | `gallery.jsx:38-49` → `filter-rail.html` hat keine Person-Facette; benötigt `person_id` auf `AssetDto` + Personen-API (kommt in P7) |
| 2 | **Framing-Facette fehlt komplett.** Design hat Framing (close_up / medium / full_body) als eigene Facette. | GROSS → sauber-verschoben P7 | `gallery.jsx:58-62` → `filter-rail.html` hat keine Framing-Facette; benötigt `framing`-Feld auf `AssetDto` aus AI-Analyse (kommt in P7) |

*Hinweis:* Sammlung-Facette wird in der Impl als Album-Filter umgesetzt (Collection-IDs statt Favoriten/Edits-Toggles) — vertretbar, da Backend albumbasiert ist.

---

### Galerie — Sub-Toolbar

**Design:** `docs/design/js/gallery.jsx:213-238`  
**Impl:** `frontend/src/app/features/galerie/sub-toolbar/sub-toolbar.html`

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Auswählen-Button ausgelagert.** Design hat "Auswählen"-Button als fünfte Kontrolle in `sb-tools`. | MITTEL → behoben | Button in `sub-toolbar.html` `subbar__tools` integriert; `galerie__sel-bar` entfernt (Phase 4). |
| 2 | **Filter-Chips ohne Kategorie-Prefix.** Design zeigt `chip-key` vor dem Chip-Label. | KLEIN → behoben | `subbar__chip-key`-Span in `sub-toolbar.html` + `chipKey`-Feld in `FilterChip` hinzugefügt (Phase 4). |

---

### Galerie — Grid-Zelle (Cell)

**Design:** `docs/design/js/gallery.jsx:108-129`  
**Impl:** `frontend/src/app/features/galerie/cell/cell.html`

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Person-Avatar in Zelle fehlt.** Design zeigt Avatar der zugehörigen Person in der Zelle (top-left, `tile-person`). | MITTEL → sauber-verschoben P7 | `gallery.jsx:122-123` → `cell.html` hat kein `tile-person`; benötigt `person_id` auf `AssetDto` (kommt in P7) |

---

### Lightbox / Detail-Ansicht

**Design:** `docs/design/README.md:93-130`, `docs/design/js/detail.jsx`  
**Impl:** `frontend/src/app/features/galerie/lightbox/lightbox.html`

**Design-Status:** vorhanden. Grundstruktur (2-Spalten, Stage links, Panel rechts) korrekt umgesetzt.

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | Gesichter-Strip fehlt | sauber-verschoben P7 | `lightbox.html:203` Kommentar "Stub-Sektionen: ausgeblendet bis P7/P8" |
| 2 | Versionen-Timeline fehlt | sauber-verschoben P8 | wie oben |

*Keine Design-Missachtungen.*

**Lore-Panel (P25 Phase 2) — Design-Lücke-erfunden (freihändig, freigegeben):** Kein Mockup.
`docs/design/js/detail.jsx` kennt kein Wissens-/Lore-Panel; Dok 050 §5 gibt nur eine Beispiel-Liste
von Sektionen vor. Umgesetzt als weitere Sektion in P15s Lightbox-Panel (`lore-panel/`), Optik über
dieselben CSS-Tokens wie die Nachbar-Sektionen (`.panel-sec`/`.rel-row`/Chips). **Bewusste Abweichung
von der 7-Sektionen-Liste aus Dok 050 §5:** gebaut als **5 domänen-agnostische Sektionen**
(Kurzbio · Beziehungen · Franchises · Eigene Bilder · Quellen). „Rollen" und „Verwandte Entitäten"
entfallen als eigene Sektionen — ihre Information steckt in „Beziehungen" (nach Beziehungstyp
beschriftet). Grund: Das Datenmodell trägt keine eigenen Felder dafür; die einzige Quelle wären die
frei editierbaren Domänen-Beziehungstypen, und die dürfen laut Domänen-Kontrakt nirgends hart
verdrahtet sein. Entscheidung Sascha (2026-07-09).

---

### Personen-View

**Design:** `docs/design/js/app.jsx:153-263` (PeopleView)  
**Impl:** `frontend/src/app/features/personen/personen.ts`

**Design-Status:** vorhanden (vollständige PeopleView im Prototyp).  
Impl: Placeholder `"Noch nicht implementiert — kommt in P7"` → **sauber-verschoben (P7)**. Keine Abweichung im aktuellen Scope.

---

### Alben-View

**Design:** `docs/design/js/albums.jsx`, `docs/design/README.md:151-155`  
**Impl:** `frontend/src/app/features/alben/alben.html`

**Design-Status:** vorhanden. Impl deckt Overview + Detail (Cover-Grid, Smart-Badge, Album-Settings-Drawer) ab.  
Keine GROSS/MITTEL-Abweichungen erkennbar. Ggf. kosmetische Kleinigkeiten (nicht weiter vertieft, da kein GROSS/MITTEL-Verdacht).

---

### Trainingssets-View

**Design:** `docs/design/js/training.jsx`  
**Impl:** `frontend/src/app/features/trainingssets/trainingssets.ts`

**Design-Status:** vorhanden (vollständiger Trainingsset-Editor im Prototyp).  
Impl: Placeholder `"Noch nicht implementiert — kommt in P10"` → **sauber-verschoben (P10)**.

---

### Review-Queue

**Design:** `docs/design/js/review.jsx` (vollständige View mit Header, Sidebar, Hauptbild)  
**Impl:** kein Feature-Ordner, kein Route `/review`

**Design-Status:** vorhanden. Kein aktiver Backlog-Plan für Review-Queue. → **sauber-verschoben** (kein Liefertermin, aber auch nicht Scope dieses Plans).

---

### Modelle-View

**Design:** `docs/design/js/models.jsx`, `models-dialogs.jsx`  
**Impl:** `frontend/src/app/features/modelle/modelle.html` + `model-card`, `model-drawer`, `download-dialog`, `bind-dialog`

**Design-Status:** vorhanden. Tier-Gruppen (Core/Optional/Generativ), Cards, Drawer, Dialoge — Grundstruktur korrekt umgesetzt. Keine GROSS/MITTEL-Abweichungen erkennbar.

---

### Wartung-View

**Design:** `docs/design/js/maintenance.jsx`  
**Impl:** `frontend/src/app/features/wartung/wartung.ts` (Inline-Template)

**Design-Status:** vorhanden. Impl deckt Status-Leiste, Scan-Sektion, Issue-Rows (orphan/missing/drift) ab. Strukturell dem Design entsprechend. Keine GROSS/MITTEL-Abweichungen.

---

### Papierkorb-View

**Design:** Im Prototyp nur Placeholder (`app.jsx:487-491`), kein dediziertes `trash.jsx`.  
**Impl:** `frontend/src/app/features/papierkorb/papierkorb.html` (vollständig: Liste mit Restore/Purge)

**Design-Status:** nur Nav-Slot.  
**Abweichungstyp:** Design-Lücke-erfunden — aber pragmatisch und konsistent (passt zu Konzept). → KLEIN, kein Handlungsbedarf.

---

### Tags-View

**Design:** Im Prototyp nur Nav-Slot in der Nav-Leiste; kein eigenes `tags.jsx`.  
**Impl:** `frontend/src/app/features/tags/tags.html` (vollständig: Liste, Suche, Rename, Merge-Dialog)

**Design-Status:** nur Nav-Slot.  
**Abweichungstyp:** Design-Lücke-erfunden.  
**Schwere:** GROSS — vollständige View ohne Mockup-Referenz, Optik freihändig erfunden.  
→ **Detailbefunde als Phase-3-Finding getaggt** (siehe FINDINGS.md).

---

### Einstellungen-View

**Design:** `docs/design/js/settings.jsx:504-518`  
**Impl:** `frontend/src/app/features/einstellungen/einstellungen.ts:41-476`

**Design-Status:** vorhanden (vollständiges `st-page` Master-Detail-Layout).

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Fehlendes Master-Detail-Layout.** Design: `st-page` mit linker `st-nav` (Icons + Labels, 6 Sektionen) + rechter `st-body` (aktive Sektion). Impl: single-column scroll, `max-width:680px`, alle Sektionen untereinander. | GROSS | `settings.jsx:504-517` `React.createElement("div", { className: "st-page" }, React.createElement("aside", { className: "st-nav" }, …), React.createElement("div", { className: "st-body" }, …))` → `einstellungen.ts:41-43` `<div class="settings-layout">` single-column |
| 2 | **Sektions-Nav fehlt komplett.** Design hat linke Nav mit Sektions-Buttons (Bibliothek, Verarbeitung, Darstellung, Bearbeitung, Tastaturkürzel, Info) + aktiven Zustand. Impl hat keine Nav — scrollt linear. | GROSS | `settings.jsx:508-512` SECTIONS.map → `st-nav-item` → nicht vorhanden in Impl |

→ **Detailbefunde als Phase-2-Finding getaggt** (siehe FINDINGS.md).

---

### Import-Dialog

**Design:** `docs/design/js/import.jsx`  
**Impl:** `frontend/src/app/ui/import-dialog/import-dialog.html`

**Design-Status:** vorhanden. Modal-Overlay implementiert. Keine GROSS/MITTEL-Abweichungen erkennbar.

---

### Editor — Generative Panels (Edit / Inpaint / Upscale)

**Design:** `docs/design/js/editor-tools.jsx` (`UpscalePanel`, `Flux2Panel`)  
**Impl:** `frontend/src/app/features/editor/` (flux2-panel = Edit, inpaint-panel, upscale-panel, resolution-field)

**Design-Status:** vorhanden, aber **bewusst überholt (P16, ADR-008).**

**Abweichungstyp:** Design-missachtet — **bewusste Entscheidung**, nicht versehentlich.

Das Mockup zeichnet P9-Parameter (SeedVR2-Modellwahl, VRAM, fp8/GGUF, Ultimate-SD-Tiles;
strength/steps/guidance/seed), die voraussetzen, dass Photofant Modelle und VRAM besitzt.
Mit dem P9-Abriss (ADR-008 ersetzt ADR-002) leben diese Werte im ComfyUI-Workflow, nicht in
Photofant. Entscheidung Sascha (2026-06-29): Panels radikal verschlanken — sie zeigen nur, was
der Workflow als Parameter exponiert (Prompt; Auflösung, falls ResolutionSelector). Modell-/
Tile-/Step-Regler entfallen ersatzlos. Das Mockup gilt für diese drei Panels als überholt.

---

## GROSS/MITTEL-Zusammenfassung (Phase-4-Ergebnis)

> Phase 4 abgeschlossen 2026-06-19.

| View | Punkt | Schwere | Status |
|---|---|---|---|
| Nav-Rail | Favoriten-Item fehlt | MITTEL | ✅ behoben (Stub + Route) |
| Nav-Rail | Review-Queue-Item fehlt | MITTEL | ✅ behoben (Stub + Route) |
| Mobile Nav | Tab-Auswahl abweichend | MITTEL | ✅ behoben ([Galerie, Personen, Favoriten, Mehr]) |
| Filter-Rail | Person-Facette fehlt | GROSS | → sauber-verschoben P7 |
| Filter-Rail | Framing-Facette fehlt | GROSS | → sauber-verschoben P7 |
| Sub-Toolbar | Auswählen-Button ausgelagert | MITTEL | ✅ behoben (in sb-tools integriert) |
| Grid-Zelle | Person-Avatar fehlt | MITTEL | → sauber-verschoben P7 |

KLEIN-Punkte:
- Nav-Rail Tags extra: ✅ entfernt (ADR-005-Cleanup)
- Nav-Rail Storage statisch: bewusst gelassen (kein Backend-Endpunkt)
- Top-Bar Import ohne Text: bewusst gelassen (icon-only genügt im Top-Bar-Kontext)
- Sub-Toolbar Chips ohne Prefix: ✅ behoben (chipKey-Feld + Span)
