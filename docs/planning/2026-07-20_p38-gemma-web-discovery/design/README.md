# Handoff: Wissen (Knowledge) Tab + Person↔Wissen-Verknüpfung

## Overview
Neuer „Wissen"-Bereich für Photofant: eine personenbezogene Wissensbasis (Bio, Merkmale, Beziehungen, Quellen) mit zwei Erfassungswegen — privates Interview (freies Q&A, vom LLM zu einem Kurzprofil verdichtet) und Web-Suche (LLM schlägt öffentlich auffindbare Fakten zur Bestätigung vor) — plus einem neuen „Wissen"-Tab in der Lightbox und einer Verknüpfungs-UI zwischen Personen und Wissens-Notizen (automatisch per Namens-Match-Vorschlag, manuell per Suche).

## About the Design Files
Die Dateien in diesem Bundle sind **Design-Referenzen in HTML/React** (Babel-in-Browser-Prototyp, kein Build-Schritt) — sie zeigen Look, Struktur und Interaktion, sind aber **kein Produktionscode zum 1:1-Kopieren**. Aufgabe: dieses Design im **bestehenden Angular-Frontend** von Photofant nachbauen (`frontend/src/app`, standalone Components, Angular Signals, NgRx-Store `knowledge`-Slice, `KnowledgeService`), mit den dort etablierten Mustern statt mit React/`React.createElement`.

Wichtig: **Der Zielort existiert bereits und ist teilweise gebaut.** Das ist kein Greenfield-Feature:
- `frontend/src/app/features/wissen/` — `wissen.ts/html/scss`, `entity-wizard-dialog/`, `interview-dialog/`, `work-queue/`
- `frontend/src/app/features/personen/` — `personen.ts/html/scss`, `person-card/`, `link-entity-dialog/`
- Backend bereits vollständig: `backend/photofant/api/knowledge.py`, `knowledge_tasks.py`, `knowledge_ai.py`, `knowledge/service.py`, `knowledge/vault.py` (Markdown-first, SQLite-Cache), Interview-/Import-/Update-Jobs.

Die Aufgabe ist überwiegend **UI/UX-Weiterentwicklung bestehender Komponenten**, nicht Neubau der Datenschicht.

## Fidelity
**Hifi für Layout/Interaktion, aber mit Mock-Daten.** Farben, Typografie, Abstände und Zustandsübergänge sind bewusst gestaltet und sollen übernommen werden. Es gibt **keine echte LLM-Anbindung** im Prototyp — Interview-Synthese, Web-Fakten und KI-Vorschläge sind statische Beispieldaten mit `setTimeout`-Ladezuständen. Die echten Endpunkte existieren bereits im Backend (`/api/knowledge/ai/*`, `/api/knowledge/interview/synthesize`, etc.) und sollen an die Stelle der Mock-Timeouts treten.

## Screens / Views

### 1. Wissen-Übersicht (`kw-wrap`)
- Kopfzeile: Titel „Wissen" (20px/700) + Untertitel (12.5px, `--text-3`) links; rechts zwei Buttons „Privates Interview" (sparkle-Icon) und „Web-Suche" (globe-Icon), Stil wie `.kw-btn` (Surface-Button, 36px hoch).
- „Offene Aufgaben"-Reihe: horizontal scrollende Chips (`.kw-task-chip`, 250px breit) mit Icon, Label, Sub-Label, X zum Verwerfen. Aufgaben-Arten: `missing_field`, `low_completeness`, `no_entity`, `suggestion`, `auto_link` (Namens-Match-Vorschlag zwischen unverknüpfter Notiz und Person).
- Personen-Grid (`.kw-grid`, `repeat(auto-fill, minmax(150px,1fr))`): eine Karte pro Person mit **Vollständigkeits-Ring** (`conic-gradient`, s. Design-Tokens) um den Avatar, Name, „N% · Domäne" oder „Kein Wissen angelegt" (kursiv, `--text-3`).
- „Nicht verknüpfte Notizen"-Sektion (nur sichtbar wenn vorhanden): Karten mit gestricheltem Rand, Titel, Vollständigkeit, Button „Verknüpfen" → öffnet Personen-Suche.
- Toast-Leiste (`.kw-toast`) für Bestätigungen (grüner Rand, check-Icon, 2.8s Anzeigedauer).

### 2. Wissen-Detail (Modal, `.kw-modal`)
- Kopf: großer Vollständigkeits-Ring (72px) um Avatar, Name (19px/700), Sub-Zeile (%, Domäne, „aktualisiert am …"), rechts drei Buttons: „Interview", „Web-Suche", „Verknüpfung lösen".
- KI-Vorschlag-Banner (`.kw-ai-banner`, wenn vorhanden): Fließtext-Vorschlag für ein fehlendes Feld + „Übernehmen"/„Verwerfen".
- Zwei-Spalten-Body (`grid-template-columns: 1fr 240px`):
  - Links: „Profil" (Fließtext-Bio), „Merkmale" (Label/Wert/Owner-Pill-Zeilen — Owner: Manuell/Web/KI-Schätzung/fehlt, je eigene Farbe), „Beziehungen" (Avatar-Chips mit Typ, z. B. „Partner:in"), „Quellen" (Icon + Label je Herkunft), „Album-Vorschlag"-Box (KI schlägt ein Album aus Fotos + Wissen vor).
  - Rechts: „Verknüpfte Fotos" — 3-spaltiges Grid quadratischer Thumbnails, Klick öffnet das Foto in der Lightbox.
- Leerer Zustand (keine Notiz vorhanden): zentrierter Avatar, Hinweistext, Buttons „Interview starten" + (wenn unverknüpfte Notizen existieren) „Bestehende Notiz verknüpfen".

### 3. Interview-Wizard (Modal, `.kw-wiz`, 500px breit)
Schritte: (0) Personen-Wahl (Quick-Chips der bekannten Personen + Freitext-Name) oder — bei Aufruf aus einem Personen-Profil — direkt Bestätigungszeile „Interview mit {Name}"; (1..N) je eine Frage im Textarea mit Fortschrittsanzeige „Frage X von N" (Leerlassen = Überspringen erlaubt); (N+1) Lade-Spinner „Antworten werden zu einem Kurzprofil zusammengefasst…"; (N+2) Zusammenfassung mit synthetisiertem Bio-Absatz + Explainability-Zeile („Aus N Antworten · Modell … · Prompt v… · Konfidenz …%"), Buttons „Antworten anpassen" (zurück) / „Übernehmen".
Fragen (austauschbar, aktuell 5): siehe `PF.KNOWLEDGE_INTERVIEW_QUESTIONS` in `js/data.js`.

### 4. Web-Suche-Wizard (Modal, gleiche Chrome wie Interview)
Schritte: (0) Personen-Wahl + optionales Hinweis-Textfeld (Links, Beruf, Stadt); (1) Lade-Spinner „Gemma durchsucht öffentliche Quellen für {Name}…"; (2) Ergebnisliste — je Fakt eine Zeile mit Checkbox (Standard: aktiv), Feldname, Wert, Quellen-Domain, Konfidenz-Pill (`score-pill high/mid`), Footer-Button „N Fakten übernehmen".

### 5. Lightbox-Tab „Wissen"
Fünfter Tab neben Übersicht/Gesichter/Versionen/Details. Zeigt für die erkannte Hauptperson: Bio-Auszug + Vollständigkeit (Section-Action „Vollständiges Profil" → springt in die Wissen-Ansicht), optionalen KI-Vorschlag-Hinweis, und „Ähnliche Bilder" (3-spaltiges Thumbnail-Grid aller anderen Fotos mit derselben Person, anklickbar zum Durchblättern). Ohne zugeordnete Person: Hinweistext auf den Gesichter-Tab. Ohne Wissen: CTA „Interview starten".

### 6. Personen-Karten-Integration (Personen-Ansicht)
Jede Personen-Karte bekommt direkt unter dem Avatar entweder einen **Wissens-Chip** (`.person-know-chip`, gefüllt, „✨ N%") bei bestehender Notiz, oder einen **Nudge** (`.person-know-nudge`, gestrichelter Rand, „Wissen anlegen?") wenn noch keine existiert — Klick auf beides öffnet die Wissen-Detailansicht für diese Person.

## Interactions & Behavior
- **Automatische Verknüpfung**: (a) Wizard mit vorbelegter Person (aus Profil/Personen-Karte gestartet) verknüpft die entstehende Notiz sofort; (b) Aufgaben-Queue schlägt Namens-Treffer zwischen unverknüpften Notizen und Personen vor (`auto_link`-Task mit Konfidenz-Prozent), ein Klick öffnet den Personen-Picker mit vorausgewähltem Top-Treffer.
- **Manuelle Verknüpfung**: aus dem leeren Profil-Zustand „Bestehende Notiz verknüpfen" (durchsucht unverknüpfte Notizen), oder aus einer unverknüpften Notiz-Karte „Verknüpfen" (durchsucht Personen). „Verknüpfung lösen" im Detail-Header trennt die Zuordnung, die Notiz bleibt als unverknüpft erhalten (kein Datenverlust).
- Wizard-Ergebnis **ohne** ausgewählte Person landet automatisch als eigenständige, unverknüpfte Notiz statt verworfen zu werden.
- Alle Modals schließen per Scrim-Klick, X-Button oder Escape (wo im Prototyp implementiert).
- Ladezustände sind reine `setTimeout`-Simulationen (1000–1100ms) — in der echten Anbindung durch die bestehenden Job-Status-Polls/SSE ersetzen (`KnowledgeLookupJob`, `InterviewJob`, `KnowledgeImportJob`/`KnowledgeUpdateJob`).

## State Management
Im Prototyp lebt der Verknüpfungs-Zustand zentral in der Root-`App`-Komponente (nicht in `Wissen` selbst), damit Personen-Ansicht und Wissen-Tab denselben Stand zeigen:
- `linkOverrides`: `{ [personId]: entity | null }` — `null` bedeutet „explizit getrennt".
- `unlinked`: Array unverknüpfter Notizen.
- `wissenFocus`: Person-ID, die beim Wechsel in den Wissen-Tab automatisch geöffnet wird (z. B. aus der Lightbox oder einer Personen-Karte).
In Angular entspricht das dem bestehenden NgRx-`knowledge`-Store (`knowledgeSelectors.selectAllEntities`, `selectAllTasks`) — die Verknüpfung selbst ist im Backend bereits als `POST /api/persons/{id}/link-entity` / Unlink modelliert (`photofant/api/persons.py`), das Frontend muss nur noch die hier gezeigten UI-Zustände (Chip/Nudge auf der Personen-Karte, „Nicht verknüpft"-Sektion im Wissen-Tab, Namens-Match-Aufgabe) ergänzen.

## Design Tokens
Aus `styles.css`:
- Flächen: `--bg #0e1013`-artig (oklch 0.165 0.006 256), `--bg-2` oklch(0.195 0.007 256), `--surface` oklch(0.225 0.008 256), `--surface-2` oklch(0.255 0.009 256), `--line` oklch(0.305 0.010 256).
- Text: `--text` oklch(0.965 0.004 256), `--text-2` oklch(0.760 0.010 256), `--text-3` oklch(0.580 0.012 256).
- Akzent: `--accent` oklch(0.685 0.135 248), `--accent-weak` (16% Alpha), `--semantic` oklch(0.700 0.150 305) (für „Web"-Owner-Pills), `--good` oklch(0.740 0.130 152), `--warn` oklch(0.800 0.130 75).
- Radius: `--radius` 10px, `--radius-s` 7px, `--radius-l` 14px.
- Schrift: `--font` Helvetica Neue/Helvetica/Arial, `--mono` IBM Plex Mono (Zahlen, Prozente, Konfidenz).
- Wissen-spezifische Klassen (alle in `styles.css`, Abschnitt „WISSEN"): `.kw-*` (Seite, Detail, Wizards, Owner-Pills, Ring via `conic-gradient(var(--accent) calc(var(--pct)*1%), var(--line) 0)`), `.person-know-chip` / `.person-know-nudge` (Personen-Karte).

## Assets
Keine neuen Bild-Assets — nutzt bestehende `randomuser.me`-Portraits (`PF.personPhoto`) und `picsum.photos`-Platzhalterfotos (`PF.picsum`) aus `js/data.js`. Icons sind Inline-SVG-Pfade in `js/icons.jsx` (neu hinzugefügt: `book`, `globe`).

## Files
- `Photofant Galerie.html` — App-Shell, Script-Reihenfolge (`js/knowledge.jsx` nach `js/training.jsx` geladen)
- `js/knowledge.jsx` — Wissen-Seite, Detail-Modal, beide Wizards, Link-Picker (neu)
- `js/detail.jsx` — Lightbox, Funktion `Lightbox()`: `tabs`-Array + `tab === "wissen"`-Render-Block (Zeilen um `knowSugg`/`relatedPics`)
- `js/app.jsx` — Nav-Eintrag „Wissen", `PeopleView()` (Wissens-Chip/Nudge auf Personen-Karten), gehobener State `kLinks`/`kUnlinked`/`wissenFocus` in `App()`
- `js/data.js` — Mock-Daten: `PF.KNOWLEDGE`, `PF.KNOWLEDGE_TASKS`, `PF.KNOWLEDGE_UNLINKED`, `PF.KNOWLEDGE_SUGGESTIONS`, `PF.KNOWLEDGE_WEB_FACTS`, `PF.KNOWLEDGE_INTERVIEW_QUESTIONS`, `PF.KFIELD_DEFS`
- `styles.css` — Abschnitt „WISSEN" (Klassen `.kw-*`) + Ergänzungen in `.person-*`
