# Phase 5 — Wissen-Übersicht nach Design

**Komplexität:** standard (Design liegt vor, Daten kommen aus bestehenden Selektoren; einzige
neue Mechanik ist der Vollständigkeits-Ring als eigene Komponente).
**Voraussetzung:** Phase 2 (Vollständigkeit im DTO) und Phase 4 (die drei neuen Aufgaben-Arten).

Heute ist die Wissen-Seite eine flache Liste aus Titel/Typ/Domäne. Das Design macht daraus eine
Personen-Übersicht mit Vollständigkeits-Ringen, einer Aufgaben-Reihe und einer Sektion für
Notizen ohne Person.

## Design-Referenz
- `design/README.md` Abschnitt „1. Wissen-Übersicht" — die verbindliche Beschreibung.
- `design/js/knowledge.jsx` — Aufbau und Zustandsübergänge (React-Prototyp, **nicht** kopieren).
- `design/styles.css` Zeile 1385-1416 (`.kw-wrap` … `.kw-ring-gap`) und 1493-1498
  (`.kw-unlinked-*`) — die Maße.

**Die Design-Tokens sind identisch mit denen der App** (`frontend/src/tailwind.css` Zeile 9-47
gegen `design/styles.css`: `--bg`, `--surface`, `--line`, `--accent`, `--semantic`, `--radius`,
`--mono` — Zeichen für Zeichen dieselben Werte). Farb- und Radius-Angaben aus dem Handoff also
wörtlich übernehmen, **keine** eigenen Werte erfinden und nichts umrechnen.

## Kontext (lesen vor dem Start)
- `frontend/src/app/features/wissen/wissen.ts` — die bestehenden Signale (Zeile 18-63): Domänen,
  Entities, Aufgaben, Autonomie, Wizard-Zustand. Die Übersicht baut darauf auf, nichts davon
  wird entfernt.
- `frontend/src/app/features/wissen/wissen.html` — die 93 Zeilen, die ersetzt werden.
- `frontend/src/app/features/wissen/work-queue/work-queue.{ts,html,scss}` — die bestehende
  Aufgaben-Anzeige, die auf die Chip-Reihe des Designs umgebaut wird (`resolve`/`dismiss`-Outputs
  bleiben, nur Darstellung und die neuen Arten kommen dazu).
- `frontend/src/app/store/persons/persons.selectors.ts` — `personsSelectors.selectAll`,
  `selectIsLoading`. Die Übersicht braucht die Personen-Liste.
- `frontend/src/app/services/person.service.ts` — `portraitUrl(faceId)` für das Avatar-Bild;
  Aufrufmuster in `person-card.ts` Zeile 95-98.
- `frontend/src/app/models/person.model.ts` — `PersonDto` mit `linked_entity: EntityRefDto | null`
  (trägt nach Phase 2 die `completeness`).
- `frontend/src/app/ui/icon/icon.ts` — verfügbare Icons. `sparkle` und `search` sind da;
  **prüfen**, ob ein Globus-Icon existiert — wenn nicht, `globe` aus `design/js/icons.jsx`
  (Inline-SVG-Pfad) in die Icon-Registry aufnehmen, kein Fremd-Paket.
- `frontend/src/app/features/personen/link-entity-dialog/` — der bestehende Verknüpfungs-Dialog,
  der aus dieser Seite heraus wiederverwendet wird (nicht neu bauen).

## Aufgabe 1 — Vollständigkeits-Ring als eigene Komponente
Neu: `frontend/src/app/ui/completeness-ring/completeness-ring.{ts,html,scss}`, Selektor
`pf-completeness-ring`. Wird in dieser Phase, in Phase 6 und in Phase 8 gebraucht — deshalb
unter `ui/`, nicht im Feature.

Eingänge: `value = input.required<number>()` (0..1), `size = input<number>(64)`,
`thickness = input<number>(4)`.

Struktur exakt nach `design/styles.css` Zeile 1414-1415:
```scss
.ring {
  border-radius: 50%;
  background: conic-gradient(var(--accent) calc(var(--pct) * 1%), var(--line) 0);
  display: grid;
  place-items: center;
  flex: none;
}
.ring__gap {
  width: calc(100% - var(--thickness) * 2);
  height: calc(100% - var(--thickness) * 2);
  border-radius: 50%;
  background: var(--bg);
  display: grid;
  place-items: center;
}
```
`--pct` und `--thickness` per `[style.--pct]`/`[style.--thickness.px]` aus den Eingängen setzen.
Im Loch steckt der projizierte Inhalt (`<ng-content>`) — Avatar-Bild oder Platzhalter-Icon.

Barrierefreiheit: `role="img"` mit `[attr.aria-label]="'Vollständigkeit ' + percent() + ' Prozent'"`.
Ohne das ist der Ring für Screenreader ein leerer Kreis.

## Aufgabe 2 — Kopfzeile
`wissen.html`, oberster Block:
- Links: `<h1>` „Wissen" (20px/700, `letter-spacing: -.015em`), darunter Untertitel 12.5px in
  `--text-3`, `max-width: 480px` — Text: „Was du über die Menschen auf deinen Fotos weißt —
  von dir erzählt oder im Netz gefunden."
- Rechts zwei Knöpfe im `.kw-btn`-Stil (36px hoch, `--surface`, 1px `--line`, `--radius` 9px,
  12.5px/600): **„Privates Interview"** (Icon `sparkle`) und **„Web-Suche"** (Icon `globe`).
  Beide öffnen die Wizards aus Phase 7.
- Der bestehende Knopf „Neue Entity" bleibt erhalten und wandert als dritter in dieselbe Reihe —
  das Design zeigt ihn nicht, aber ohne ihn gäbe es keinen Weg mehr, eine nicht-personenbezogene
  Wissenseinheit (Film, Ort) anzulegen. Weglassen wäre ein Funktionsverlust, kein Design-Gewinn.
- **„Web-Suche" ist ausgeblendet**, wenn `aiAutonomy()?.discovery !== 'auto'` — derselbe
  Schalter wie im Backend-Guard.

## Aufgabe 3 — Aufgaben-Reihe
`work-queue` umbauen: aus der bisherigen Darstellung wird die horizontal scrollende Chip-Reihe
(`design/styles.css` Zeile 1395-1405). Ein Chip: 250px breit, `flex: none`, Icon-Kachel 26px
(`--surface-2`, `--accent`), Label 12.5px/600, Sub-Label 11px `--text-3`, rechts ein
X-Knopf (20px) zum Verwerfen.

Überschrift der Reihe: „Offene Aufgaben" — 10.5px, Großbuchstaben, `letter-spacing: .12em`,
`--text-3`.

Je Aufgaben-Art Icon, Text und Klick-Ziel:

| Art | Icon | Label | Sub | Klick öffnet |
|---|---|---|---|---|
| `missing_field` | `edit` | „{Feldliste} fehlt/fehlen" | Entity-Titel | Wissen-Detail (Phase 6) |
| `low_completeness` | `warning` | „Profil kaum ausgefüllt ({N} %)" | Entity-Titel | Wissen-Detail |
| `no_entity`/`new_person` | `user` | „Noch kein Wissen angelegt" | „{Name} · {N} Fotos" | Interview-Wizard mit vorbelegter Person |
| `auto_link` | `link` | „Notiz „{Titel}" ähnelt Person {Name}" | „{N} % Namens-Übereinstimmung — verknüpfen?" | Verknüpfungs-Dialog mit vorgewähltem Treffer |
| bestehende Arten | wie heute | wie heute | wie heute | wie heute |

Gibt es für eine Art kein passendes Icon in der Registry, das nächstliegende vorhandene nehmen —
**kein** neues SVG erfinden, außer für `globe` (Aufgabe „Kontext").

Prozentwerte immer über `--mono` und als ganze Zahl (`Math.round(value * 100)`), nie mit
Nachkommastelle. Eine eigene kleine Pipe dafür ist Overkill; eine `percent()`-Hilfsmethode auf
der Komponente reicht.

## Aufgabe 4 — Personen-Grid
`.kw-grid`: `display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 16px;`

Eine Karte je Person aus `personsSelectors.selectAll` (Reihenfolge: wie der Store sie liefert;
Personen mit `is_unknown === true` werden übersprungen). Karte (`.kw-card`, `--radius-l`,
`--surface`, 1px `--line`, 18px/10px Innenabstand, mittig, 9px Abstand):
1. `pf-completeness-ring` mit `[size]="64"`, darin das Portrait über `portraitUrl(...)`, sonst
   ein `user`-Icon.
2. Name (13px/600) — bei `name === null` „Unbenannt".
3. Meta-Zeile (11px, `--text-3`, `--mono`): `„{N} % · {Domäne}"` bei verknüpfter Entity, sonst
   kursiv und ohne Mono: „Kein Wissen angelegt".

Klick auf die Karte öffnet das Detail (Phase 6) — in dieser Phase reicht ein Output
`(openDetail)`, den `wissen.ts` in ein Signal schreibt; das Modal selbst kommt in Phase 6.
Bis dahin bleibt das Signal ungenutzt, das ist gewollt und keine tote Zeile.

Eigene Komponente `features/wissen/person-knowledge-card/`, nicht inline im Template — sie wird
in Phase 6 nicht, in Phase 8 aber sinngemäß gespiegelt und ist mit Ring + drei Zuständen groß
genug für eine eigene Datei.

## Aufgabe 5 — Nicht verknüpfte Notizen
Sektion **nur sichtbar**, wenn es Entities gibt, deren `media_links.persons` leer ist **und**
deren Domäne privat ist. Berechnung als `computed()` in `wissen.ts` aus `entities()` und
`domains()` — kein neuer Endpunkt.

Überschrift wie die Aufgaben-Reihe (10.5px, Großbuchstaben). Grid
`repeat(auto-fill, minmax(220px, 1fr))`, Karte `.kw-unlinked-card`: gestrichelter Rand
(`1px dashed var(--line-2)`), Icon-Kachel 30px, Titel 12.5px/600, Meta-Zeile in `--mono`
(„{N} % · geändert am {Datum}"), rechts ein Knopf „Verknüpfen" → öffnet den bestehenden
`link-entity-dialog` im Personen-Such-Modus.

## Aufgabe 6 — Toast
Die zwei bestehenden Bestätigungs-Blöcke (`lastCreatedEntity`, `lastUpdatedEntity`) durch die
Toast-Leiste des Designs ersetzen (`design/styles.css` Zeile 1393): grüner Rand
(`oklch(0.55 0.15 150 / .35)`), Hintergrund `oklch(0.55 0.15 150 / .14)`, `--good` als
Textfarbe, `check`-Icon, 12.5px. **2,8 Sekunden sichtbar**, dann automatisch weg — über ein
Signal mit `setTimeout` im Komponenten-Kontext (`DestroyRef`-Cleanup nicht vergessen, sonst
feuert der Timer nach dem Verlassen der Seite ins Leere).

## Idiotensicherheit
- Der leere Zustand (keine Personen, keine Entities) sagt, **was zu tun ist**, nicht nur dass
  nichts da ist: „Noch nichts gespeichert. Fang mit einem privaten Interview an — fünf Fragen,
  zwei Minuten." plus der Interview-Knopf direkt darunter.
- Der Knopf „Web-Suche" bekommt ein `title` mit einem Satz, was passiert: „Sucht öffentlich
  verfügbare Angaben zu einer Person — du entscheidest danach, was übernommen wird."
- Der Vollständigkeits-Ring ist ohne Erklärung ein hübscher Kreis. Die Meta-Zeile mit „{N} %"
  steht deshalb **immer** darunter, nie nur der Ring allein.

## AK dieser Phase
- [ ] Kopfzeile: Titel 20px/700 links mit Untertitel, rechts die drei Knöpfe in einer Reihe,
      36px hoch; „Web-Suche" fehlt, solange die Einstellung auf `off` steht.
- [ ] Aufgaben-Reihe scrollt horizontal, Chips sind 250px breit, jede der drei neuen Arten
      rendert mit eigenem Icon, Label und Sub-Label.
- [ ] Personen-Grid füllt sich automatisch (`minmax(150px, 1fr)`), jede Karte zeigt Ring,
      Namen und Meta-Zeile; ohne verknüpfte Entity steht dort kursiv „Kein Wissen angelegt".
- [ ] Der Ring zeigt bei 40 % sichtbar zwei Fünftel in `--accent`, den Rest in `--line`.
- [ ] Sektion „Nicht verknüpfte Notizen" erscheint **nur**, wenn es mindestens eine gibt.
- [ ] Toast erscheint nach dem Anlegen und verschwindet nach 2,8 Sekunden von selbst.
- [ ] Leerer Zustand nennt einen konkreten nächsten Schritt und bietet den Knopf dazu.
- [ ] `npx tsc --noEmit` grün, Produktions-Build läuft durch.

## Doc-Updates
- [ ] `docs/code-map.md` — Wissen-Zeile um `ui/completeness-ring/` und
      `features/wissen/person-knowledge-card/` ergänzen.

## Report-Back
