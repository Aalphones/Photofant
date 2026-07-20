# Lightbox: Detail-Panel auf Tab-Layout umstellen

Auslöser: Commit `d5d0695` (`docs/design/js/detail.jsx` + `docs/design/styles.css`) stellt den
Design-Prototyp des Lightbox-Panels von einem langen Scroll auf ein Layout mit fixem Header,
3 Tabs (Übersicht / Gesichter / Versionen), scrollbarem Body pro Tab und einer fixen
Aktions-Fußzeile um. Die echte Komponente (`frontend/src/app/features/galerie/lightbox/`)
soll dieselbe Struktur bekommen — hat aber mehr Sektionen als der Prototyp (Wissen-Panel,
Empfehlungen, Klassifizierung, erweiterte Aktionen, Beziehungen/Quelle), für die im Mockup
keine Zuordnung existiert. Zuordnung wurde mit dem User abgestimmt (siehe unten).

## Entschiedene Zuordnung (User-Freigabe 2026-07-20)

- **Übersicht-Tab:** Wissen-Panel (`pf-lore-panel`), Empfehlungen, Metadaten,
  Generierungs-Metadaten, Caption, Tags, Klassifizierung.
- **Gesichter-Tab:** Gesichter-Sektion (Liste + Schnellzuweisung) — **nur im Asset-Modus
  sichtbar**, im Gesichter-Modus (`isFaceMode()`) ist der Tab komplett ausgeblendet (Bugfix,
  siehe unten).
- **Versionen-Tab:** Versionen-Sektion + Beziehungen (Asset-Modus) bzw. Quelle
  (Gesichter-Modus).
- **Fixe Fußzeile (immer sichtbar, unabhängig vom Tab):** die bisherige „Aktionen"-Sektion —
  Asset-Modus: Papierkorb, Klassifizieren, Explorer, Upscale. Gesichter-Modus: Person
  zuweisen, Löschen, Explorer. Ohne Sektions-Titel „Aktionen" (Fußzeile braucht keinen,
  analog zum Prototyp-Fußzeilen-Button-Row ohne Label).

**Mitgefixter Bug (User-Freigabe):** Die „Gesichter"-Sektion wird heute auch im
Gesichter-Modus gerendert (dort immer der Leer-Zustand mit „Extrahieren nochmal probieren" —
der Button greift ins Leere, weil `asset()` in dem Modus `null` ist). Mit der Umstellung wird
der Gesichter-Tab-Button **und** sein Body-Inhalt zusätzlich an `!isFaceMode()` geknüpft.

## Betroffene Dateien

- `frontend/src/app/features/galerie/lightbox/lightbox.ts`
- `frontend/src/app/features/galerie/lightbox/lightbox.html`
- `frontend/src/app/features/galerie/lightbox/lightbox.scss`

## Finale Akzeptanzkriterien (fürs Gesamtergebnis)

1. Panel zeigt fix (immer sichtbar, scrollt nicht mit): Header (Avatar+Name+Datum) oben,
   3-Tab-Leiste darunter (2 Tabs im Gesichter-Modus), Aktions-Fußzeile unten.
2. Zwischen Header/Tabs und Fußzeile scrollt nur der Body des aktiven Tabs — nicht das ganze
   Panel.
3. Tab-Wechsel per Klick auf `overview`/`people`/`versions`; aktiver Tab visuell hervorgehoben
   (Unterstrich in Akzentfarbe, analog Prototyp `.panel-tab.active`).
4. Beim Wechsel auf ein anderes Asset/Face (Pfeiltasten, Klick auf verwandtes Bild) springt der
   aktive Tab zurück auf `overview` (analog Prototyp `setTab("overview")` im Reset-Effect).
5. Gesichter- und Versionen-Tab zeigen Badges mit der jeweiligen Anzahl (`faces().length` /
   `activeVersions().length`), Übersicht-Tab hat kein Badge.
6. Gesichter-Modus: kein Gesichter-Tab-Button, kein Gesichter-Tab-Inhalt (Bugfix).
7. Keine Funktionalität geht verloren — jede Aktion/jedes Feld, das heute erreichbar ist,
   bleibt erreichbar (nur an neuer Stelle). Kein Verhalten außerhalb der Tab-/Fußzeilen-
   Umsortierung ändert sich.
8. `ng build` läuft ohne neue Fehler/Warnungen durch.

## Smoke-Checkliste (User, nach Umsetzung)

Wackelstellen zuerst (dort bin ich mir am unsichersten):

1. 🟡 **Gesichter-Modus öffnen** (ein Gesicht direkt anklicken/öffnen, nicht über ein Asset) —
   zeigt das Panel nur 2 Tabs (Übersicht/Versionen), keinen toten Gesichter-Tab mehr? Zeigt
   die Fußzeile „Person zuweisen / Löschen / Explorer"?
2. 🟡 **Tab-Wechsel + Scroll-Verhalten**: in „Übersicht" weit runterscrollen (bis Klassifizierung
   sichtbar), dann auf „Versionen" wechseln — bleibt die Fußzeile unten fix stehen, ist der
   Versionen-Tab-Inhalt oben und nicht mitten im Scroll?
3. Asset mit Empfehlungen + Wissen-Verknüpfung öffnen — beide Sektionen im Übersicht-Tab
   sichtbar und funktional (Klick auf Empfehlung öffnet das Bild, Wissen-Link navigiert)?
4. Tags hinzufügen/entfernen, Caption bearbeiten — beides jetzt im Übersicht-Tab, Verhalten
   unverändert?
5. Asset mit Original+verknüpften Edits öffnen — Beziehungen jetzt im Versionen-Tab,
   Zuordnen/Entfernen funktioniert weiterhin?
6. Bild wechseln (Pfeiltaste) — Tab springt zurück auf „Übersicht"?
7. Mobile-Breite (< 640px) — Panel liegt weiterhin unten an, Fußzeile/Tabs nicht abgeschnitten?

## Phasen

| # | Titel | Rating | Status |
|---|---|---|---|
| 1 | TS-State + HTML-Restrukturierung (Tabs, Footer, Sektionen umsortieren) | standard | ✅ complete |
| 2 | SCSS für Tab-Leiste, scrollbaren Body, fixe Fußzeile | mechanisch | ✅ complete |

---

## Phase 1 — TS-State + HTML-Restrukturierung

### Kontext

- `lightbox.ts` — insbesondere: der Reset-`effect()` im Constructor (ca. Zeile 711-737, setzt
  `showGenMeta`, `addingTag`, `editingCaption` etc. bei Asset-/Face-Wechsel zurück),
  `isFaceMode` (Zeile 186), `faces` (Zeile 546), `activeVersions` (Zeile 256).
- `lightbox.html` — komplette Panel-Sektion (Zeile 66-608). Die Blöcke, die verschoben werden,
  bleiben inhaltlich (Bindings, `@if`-Bedingungen innerhalb der Sektion, Klassen) **exakt**
  erhalten — nur ihre Position im Baum und ihre umschließenden `@if`/`@else`-Gates ändern sich.
- Prototyp zur Orientierung (nicht kopieren, nur Struktur-Referenz):
  `docs/design/js/detail.jsx` Zeilen ~229-397 (Tab-State, Tab-Bar, `panel-body`).

### Akzeptanzkriterien dieser Phase

- Neues Signal `activeTab = signal<'overview' | 'people' | 'versions'>('overview')` in
  `lightbox.ts`, direkt bei den anderen einfachen UI-State-Signalen (z.B. neben `showGenMeta`).
- Der bestehende Reset-`effect()` (der bei Asset-/Face-Wechsel div. State zurücksetzt) bekommt
  zusätzlich `this.activeTab.set('overview');`.
- Kein neues `tabs`-Array/Computed — die 3 (bzw. 2) Tab-Buttons werden direkt im Template
  geschrieben (Labels sind fix auf Deutsch, kein Loop nötig — Konvention: keine Abstraktion für
  eine einmalige Verwendung).
- HTML-Struktur von `.panel` (Zeile 67 in `lightbox.html`) nach dem `@if (panelReady())`:
  1. Header-Block (aktuell Zeile 71-86) — **unverändert**, nur Klasse `panel-fixed` zusätzlich
     zu `panel-sec panel-header`.
  2. Neue Tab-Leiste (`<div class="panel-tabs">`) mit 2-3 `<button class="panel-tab" ...>`:
     - „Übersicht" — immer sichtbar, `(click)="activeTab.set('overview')"`,
       `[class.active]="activeTab() === 'overview'"`.
     - „Gesichter" — **nur `@if (!isFaceMode())`**, mit Badge `{{ faces().length }}`
       (`<span class="tab-badge">{{ faces().length }}</span>`), `(click)="activeTab.set('people')"`.
     - „Versionen" — immer sichtbar, Badge `{{ activeVersions().length }}`,
       `(click)="activeTab.set('versions')"`.
  3. Neuer scrollbarer Body-Container `<div class="panel-body">`, darin:
     - `@if (activeTab() === 'overview') { ... }` — enthält in dieser Reihenfolge:
       a. Lore-Panel-Block (aktuell Zeile 88-96) — unverändert hierher verschieben.
       b. Empfehlungen-Block (aktuell Zeile 185-208, das `@if (showRecommendations())`) —
          unverändert hierher verschieben.
       c. `@if (!isFaceMode())`-Block, darin unverändert (nur ohne die „Aktionen"-Sektion, die
          geht in die Fußzeile, siehe Schritt 4):
          - Metadaten-Sektion (aktuell Zeile 253-338)
          - Generierungs-Metadaten (aktuell Zeile 340-361)
          - Caption-Sektion (aktuell Zeile 363-389)
          - Tags-Sektion (aktuell Zeile 391-448)
          - Klassifizierung (aktuell Zeile 450-469)
     - `@if (!isFaceMode() && activeTab() === 'people') { ... }` — enthält unverändert den
       kompletten Gesichter-Block (aktuell Zeile 98-183, beide Zweige `faces().length > 0` /
       `@else`).
     - `@if (activeTab() === 'versions') { ... }` — enthält:
       - Versionen-Sektion (aktuell Zeile 473-502) unverändert.
       - `@if (isFaceMode()) { ... } @else { ... }`: Quelle-Block (aktuell Zeile 531-544) bzw.
         Beziehungen-Block (aktuell Zeile 548-603), beide unverändert.
  4. Neue fixe Fußzeile **außerhalb** von `.panel-body`, z.B. `<div class="panel-actions-fixed">`:
     - `@if (!isFaceMode()) { ... } @else { ... }` — Inhalt ist der bisherige „Aktionen"-Block
       für Asset-Modus (aktuell Zeile 213-251, **ohne** den `<div class="psec-title">Aktionen</div>`-
       Titel — nur die `pbtn-row`-Divs und den `upscale-error`) bzw. für Gesichter-Modus
       (aktuell Zeile 507-529, ebenfalls ohne Titel-Div).
- Nichts an den Bindings/Methoden/Bedingungen *innerhalb* der verschobenen Blöcke ändert sich —
  reines Verschieben + neue umschließende `@if`-Gates. Keine neuen TS-Methoden nötig
  (`activeTab.set(...)` wird direkt im Template aufgerufen, wie bei anderen Signalen in dieser
  Datei üblich, z.B. `captionDraft.set(...)`).

### Checkliste

- [x] `activeTab`-Signal in `lightbox.ts` ergänzt
- [x] Reset-Effect setzt `activeTab` zurück auf `'overview'`
- [x] `lightbox.html`: Header bekommt `panel-fixed`-Klasse
- [x] `lightbox.html`: Tab-Leiste eingefügt (Übersicht/Gesichter/Versionen, Gesichter nur
      außerhalb Face-Modus, Badges korrekt)
- [x] `lightbox.html`: `panel-body`-Wrapper mit 3 tab-bedingten Blöcken, Inhalte wie oben
      beschrieben verschoben
- [x] `lightbox.html`: fixe Fußzeile mit den bisherigen Aktionen-Inhalten (ohne Sektionstitel)
- [x] Keine verwaisten `panel-sec`-Divs oder doppelten Bindings übrig (Diff gegen Original
      gegenlesen: jede verschobene Zeile taucht genau einmal auf)
- [x] `ng build` (oder `tsc --noEmit` + Angular-Compiler-Check) läuft fehlerfrei

---

## Phase 2 — SCSS für Tab-Leiste, scrollbaren Body, fixe Fußzeile

### Kontext

- `lightbox.scss` — insbesondere `.panel` (Zeile 101-112, aktuell `overflow-y: auto` direkt am
  Panel — muss weg, Scroll wandert in den neuen Body), `.panel-sec` (Zeile 114-117),
  `.psec-title` (Zeile 175-193), `.pbtn-row`/`.pbtn` (Zeile 289-345).
- Prototyp-CSS zur Orientierung (Werte/Optik übernehmen, Klassen an bestehende Namenskonvention
  anpassen — siehe unten): `docs/design/styles.css`, Diff-Abschnitt „tab bar" +
  „scrollable body" (siehe Commit `d5d0695`, im Kontext dieses Plans oben zitiert).

### Akzeptanzkriterien dieser Phase

- `.panel`: `overflow-y: auto` entfernen, stattdessen `overflow: hidden` (bleibt
  `display:flex; flex-direction:column`).
- Neue Klasse `.panel-fixed { flex: none; }` (für Header und ggf. andere fixe Blöcke).
- Neue Klassen für die Tab-Leiste:
  - `.panel-tabs { display:flex; flex:none; border-bottom:1px solid var(--line); padding:0 8px; }`
  - `.panel-tab { flex:1; display:flex; align-items:center; justify-content:center; gap:6px;
    height:42px; font-size:12px; font-weight:600; color:var(--text-3); background:none;
    border:none; border-bottom:2px solid transparent; cursor:pointer; }`
  - `.panel-tab:hover { color: var(--text-2); }`
  - `.panel-tab.active { color: var(--text); border-bottom-color: var(--accent); }`
  - `.tab-badge { font-size:10px; font-weight:700; font-family:var(--mono); color:var(--text-3);
    background:var(--surface-2); border-radius:999px; padding:1px 6px; min-width:16px;
    text-align:center; }`
  - `.panel-tab.active .tab-badge { color: var(--accent); }`
- Neue Klasse `.panel-body { flex:1; min-height:0; overflow-y:auto;
  -webkit-overflow-scrolling: touch; }` — das ist der einzige scrollende Bereich im Panel.
- Neue Klasse `.panel-actions-fixed { flex:none; border-top:1px solid var(--line); padding:14px 18px; }`
  — die darin liegenden `.pbtn-row`-Divs (unverändert, bestehende Klasse wiederverwenden)
  brauchen keine eigene Anpassung.
- Bestehende `.panel-sec`/`.psec-title`-Regeln bleiben unangetastet (werden weiter für die
  Sektionen innerhalb der Tabs gebraucht).
- Mobile Media-Query (`@media (max-width: 640px)` bei `.panel`, aktuell Zeile 108-111) bleibt
  wie sie ist (kein Bottom-Sheet-Umbau wie im Prototyp — außerhalb des Scopes dieses Plans).

### Checkliste

- [x] `.panel` auf `overflow: hidden` umgestellt
- [x] `.panel-fixed`, `.panel-tabs`, `.panel-tab`, `.tab-badge`, `.panel-body`,
      `.panel-actions-fixed` ergänzt
- [x] Visuell: aktiver Tab zeigt Akzent-Unterstrich, inaktive Tabs `text-3`, Hover `text-2`
      (CSS gesetzt, visuelle Endkontrolle im User-Smoke-Test)
- [x] Visuell: Fußzeile hat sichtbaren `border-top`, bleibt unten fixiert
- [x] `ng build` fehlerfrei

---

## Summary

Panel auf fixen Header + Tab-Leiste (Übersicht/Gesichter/Versionen) + scrollbaren Body pro Tab
+ fixe Aktions-Fußzeile umgestellt, analog Design-Prototyp `d5d0695`. Alle bisherigen
Sektionen wurden 1:1 verschoben (keine Logik-/Binding-Änderung), zusätzlich Bugfix: Gesichter-
Tab existiert im Gesichter-Modus nicht mehr (vorher toter „Extrahieren nochmal probieren"-
Button ohne Wirkung).

## Files touched

- `frontend/src/app/features/galerie/lightbox/lightbox.ts` — `activeTab`-Signal + Reset im
  bestehenden Asset-/Face-Wechsel-Effect
- `frontend/src/app/features/galerie/lightbox/lightbox.html` — Panel komplett restrukturiert
  (Tab-Leiste, `panel-body`, `panel-actions-fixed`), keine Bindings/Methoden geändert
- `frontend/src/app/features/galerie/lightbox/lightbox.scss` — neue Klassen für Tab-Leiste,
  scrollbaren Body, fixe Fußzeile; `.panel` von `overflow-y: auto` auf `overflow: hidden`

## Commits

`47566fc` — feat(lightbox): rebuild detail panel as tabbed layout (beide Phasen)

## Deviations from plan

Keine — Umsetzung folgt dem Plan 1:1.

## Follow-ups

- Design-Prototyp (`docs/design/js/detail.jsx`/`styles.css`) selbst hinkt der echten
  Lightbox weiterhin hinterher (Wissen-Panel, Empfehlungen, Klassifizierung existieren dort
  nicht) — kein Follow-up-Zwang, nur zur Kenntnis für künftige Design-Abgleiche.
