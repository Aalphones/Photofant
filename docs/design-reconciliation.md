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
| 1 | **Favoriten-Nav-Item fehlt.** Design hat Favoriten als eigenständigen Main-Eintrag mit Count-Badge. Impl hat weder Route `/favoriten` noch Nav-Item. | MITTEL | `app.jsx:21` `{ id: "favourites", icon: "star", label: "Favoriten", count: favs }` → kein Eintrag in `nav-rail.ts:29-35` |
| 2 | **Review-Queue-Nav-Item fehlt.** Design listet Review-Queue unter Verwaltung (count=7). Kein Route `/review`, kein Nav-Item. | MITTEL | `app.jsx:25` `{ id: "review", icon: "face", label: "Review-Queue", count: 7 }` → nicht in `nav-rail.ts:37-42` |
| 3 | **Tags extra im Nav** (nicht im Design-Nav). Design kennt Tags nur intern; Impl hat Tags als vollwertigen Main-Nav-Eintrag. | KLEIN | Design: kein tags-Eintrag → `nav-rail.ts:33` `{ id: 'tags', icon: 'tag', label: 'Tags' }` |
| 4 | **Storage-Indikator statisch.** Design zeigt echte Werte (GB, Assets, Personen, %). Impl zeigt "Bibliothek leer · 0% · —". | KLEIN | `app.jsx:52-58` mit echten Daten → `nav-rail.html:48-55` hardcoded "Bibliothek leer", 0% |

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
| 1 | **Tab-Auswahl abweichend.** Design: [Galerie, Personen, Favoriten, Mehr]. Impl: [Galerie, Personen, Alben, Einstellungen]. Favoriten fehlt; Mehr-Button fehlt; stattdessen direkte Alben- und Einstellungen-Links. | MITTEL | `app.jsx:284-296` vier Tabs inkl. Favoriten/Mehr → `shell.html:51-68` vier direkte routerLinks |

---

### Galerie — Filter-Rail

**Design:** `docs/design/js/gallery.jsx:24-83`  
**Impl:** `frontend/src/app/features/galerie/filter-rail/filter-rail.html`

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Person-Facette fehlt komplett.** Design hat Person-Facette als erste Facette mit Avatar-Chips. | GROSS | `gallery.jsx:38-49` `React.createElement(Facet, { title: "Person" }, PF.PERSONS.map(…))` → nicht in `filter-rail.html` |
| 2 | **Framing-Facette fehlt komplett.** Design hat Framing (close_up / medium / full_body) als eigene Facette. | GROSS | `gallery.jsx:58-62` `React.createElement(Facet, { title: "Framing" }, …)` → nicht in `filter-rail.html` |

*Hinweis:* Sammlung-Facette wird in der Impl als Album-Filter umgesetzt (Collection-IDs statt Favoriten/Edits-Toggles) — vertretbar, da Backend albumbasiert ist.

---

### Galerie — Sub-Toolbar

**Design:** `docs/design/js/gallery.jsx:213-238`  
**Impl:** `frontend/src/app/features/galerie/sub-toolbar/sub-toolbar.html`

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Auswählen-Button ausgelagert.** Design hat "Auswählen"-Button als fünfte Kontrolle in `sb-tools`. Impl hat ihn in einem separaten `galerie__sel-bar` außerhalb der Sub-Toolbar. | MITTEL | `gallery.jsx:237-238` `selectbtn selMode` → `galerie.html:11-19` `class="galerie__sel-bar"` |
| 2 | **Filter-Chips ohne Kategorie-Prefix.** Design zeigt `chip-key` (z.B. "Person:", "Quelle:") vor dem Chip-Label. Impl hat nur das Label. | KLEIN | `gallery.jsx:219` `c.key && React.createElement("span", { className: "chip-key" }, c.key + ":")` → `sub-toolbar.html:13` kein key-prefix |

---

### Galerie — Grid-Zelle (Cell)

**Design:** `docs/design/js/gallery.jsx:108-129`  
**Impl:** `frontend/src/app/features/galerie/cell/cell.html`

| # | Punkt | Schwere | Belege |
|---|---|---|---|
| 1 | **Person-Avatar in Zelle fehlt.** Design zeigt Avatar der zugehörigen Person in der Zelle (top-left, `tile-person`). | MITTEL | `gallery.jsx:122-123` `React.createElement("div", { className: "tile-person" }, React.createElement(Avatar, { personId: a.personId, size: 22 }))` → nicht in `cell.html` |

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

## GROSS/MITTEL-Zusammenfassung (Phase-4-Kandidaten)

Alle übrigen Views (alles außer Einstellungen → Phase 2, Tags → Phase 3):

| View | Punkt | Schwere |
|---|---|---|
| Nav-Rail | Favoriten-Item fehlt | MITTEL |
| Nav-Rail | Review-Queue-Item fehlt | MITTEL |
| Mobile Nav | Tab-Auswahl abweichend (Favoriten fehlt, Mehr-Button fehlt) | MITTEL |
| Filter-Rail | Person-Facette fehlt | GROSS |
| Filter-Rail | Framing-Facette fehlt | GROSS |
| Sub-Toolbar | Auswählen-Button ausgelagert (kein sb-tools-Mitglied) | MITTEL |
| Grid-Zelle | Person-Avatar fehlt | MITTEL |

KLEIN-Punkte (nachrangig):
- Nav-Rail: Tags extra im Nav
- Nav-Rail: Storage-Indikator statisch
- Top-Bar: Import ohne Text-Label
- Sub-Toolbar: Chips ohne Kategorie-Prefix
