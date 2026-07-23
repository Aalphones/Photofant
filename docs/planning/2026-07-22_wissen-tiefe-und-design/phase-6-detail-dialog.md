# Phase 6 — Detail-Dialog: Album-Button + KI-Banner ans Design

**Rating:** standard

Die letzten beiden sichtbaren Lücken zwischen Mockup und Bau.

## Kontext — das musst du lesen

- Mockup `…\design_handoff_photofant\wissen-feature\js\knowledge.jsx`, Funktion `KDetail`
  (Zeilen 131-219) — insbesondere der `kw-album-sugg`-Block (206-212) und der
  `kw-ai-banner`-Block (168-176). `styles.css`, Abschnitt „WISSEN".
- `frontend/src/app/features/wissen/knowledge-detail-dialog/knowledge-detail-dialog.html`
  (Zeilen 93-146 = KI-Banner, 206-219 = Foto-Spalte) + `.ts` + `.scss`.
- `frontend/src/app/services/collection.service.ts` → `createCollection(request)` (Zeile 30)
  und der zugehörige `CreateCollectionRequest`-Typ. **Alben heißen im Backend `collections`.**
- `backend/photofant/api/collections.py` → `POST ""` (Zeile 315) als Kontrakt-Referenz.
- `docs/conventions/angular.md`

## Teil A — Album aus den verknüpften Fotos

Das Mockup zeigt hier eine Attrappe („6 Fotos + Wissen deuten auf ein Album ‚Sommerurlaub 2025'
hin") mit hartkodiertem Titel. **Entscheidung (mit dem Plan freigegeben):** Wir bauen keine
erfundene KI-Einsicht nach, sondern die ehrliche, sofort nützliche Variante — eine Zeile, die
sagt, wie viele Fotos verknüpft sind, und daraus auf Knopfdruck ein echtes Album anlegt.

### AK Teil A

1. Unter den Sektionen der linken Spalte steht eine Album-Zeile, sichtbar **nur**, wenn
   mindestens ein verknüpftes Foto existiert.
2. Sie nennt die Anzahl der verknüpften Fotos.
3. Ein Klick auf „Album daraus anlegen" öffnet ein Titel-Eingabefeld, vorbelegt mit dem
   Namen der Person/Notiz.
4. „Anlegen" erzeugt über `createCollection` ein Album mit genau diesen Asset-Ids.
5. Nach Erfolg zeigt die Zeile „Album ‚<Titel>' wurde angelegt." und der Button ist weg.
6. Schlägt das Anlegen fehl, erscheint eine Klartext-Fehlerzeile; der Dialog bleibt bedienbar.

### Checkliste Teil A

- [x] `CreateCollectionRequest` lesen und prüfen, welches Feld die Asset-Ids trägt und ob ein
      Typ/Modus („manuell" vs. „smart") gesetzt werden muss. **Nicht raten** — Backend-Zeile 315
      ist die Quelle. Ergebnis: Der Request trägt **keine** Asset-Ids (`name`, `kind`,
      `match_mode`) — zwei Aufrufe nötig: `createCollection({name, kind:'album'})`, dann
      `addItems(collectionId, assetIds)`.
- [x] In `knowledge-detail-dialog.ts`: `CollectionService` injizieren; Signale
      `albumFormOpen`, `albumTitle`, `albumPending`, `albumCreatedTitle`, `albumError`.
- [x] `createAlbum()`: Asset-Ids aus `relatedPhotos()` (die sind bereits auf `kind === 'asset'`
      gefiltert), `createCollection` aufrufen, Zustände setzen.
- [x] Template: Album-Zeile nach der Quellen-Sektion, Klassen im Stil der bestehenden
      `.kd-section`; das Mockup-Vorbild ist `.kw-album-sugg` (Icon `layers`, Text, Button).
- [x] `.scss` entsprechend ergänzen.

## Teil B — KI-Banner ans Design, Opt-in bleibt

Das Mockup zeigt den KI-Vorschlag **sofort beim Öffnen**. Der Bestand verlangt bewusst einen
Klick, weil sonst jedes Öffnen eines Profils einen echten Gemma-Lauf auslöst (P38-Prinzip: KI
nur auf explizite Aktion). **Entscheidung: Opt-in bleibt.** Geändert wird nur die Optik und die
Selbsterklärung — der heutige Auslöser ist ein schmaler Button, der wie eine Randnotiz wirkt und
nicht sagt, was passiert.

### AK Teil B

1. Der Auslöser sitzt an der Stelle des Design-Banners (volle Breite, zwischen Kopfzeile und
   Spalten) und sieht aus wie `.kw-ai-banner` — nicht wie ein Textlink.
2. Er benennt Nutzen **und** Kosten in einem Satz, z.B. „Gemma kann aus Fotos und vorhandenem
   Wissen eine Ergänzung vorschlagen — startet einen Modell-Lauf."
3. Kein Modell-Lauf ohne Klick (unverändert; als AK festgehalten, damit die Phase es nicht
   versehentlich kippt).
4. Lade-, Ergebnis-, Fehler- und Übernommen-Zustand behalten ihr heutiges Verhalten und liegen
   im selben Banner-Rahmen.
5. `npm run lint`, `npm run build` grün.

### Checkliste Teil B

- [x] `knowledge-detail-dialog.html` Zeilen 93-98: den `.kd-ai-prompt`-Button auf die
      Banner-Struktur umbauen (Icon + Text + Aktion rechts), Text nach AK 2.
- [x] `.scss`: `.kd-ai-prompt` entfernt (unbenutzt), Auslöser nutzt jetzt direkt `.kd-ai-banner`
      (Rahmen, Innenabstand, volle Breite kommen von dort — kein separates Angleichen nötig).
- [x] Die vier Folgezustände unverändert lassen — nur geprüft, dass sie optisch im selben Rahmen
      sitzen (gleiche `.kd-ai-banner`-Klasse, keine Änderung an deren Logik).

## Docs

- [x] `docs/design-reconciliation.md`: Zeile für den Wissen-Detail-Dialog aktualisiert —
      Album-Box bewusst abweichend (ehrlicher Button statt Attrappe), KI-Banner bewusst Opt-in.
      Beides mit einem Halbsatz Begründung, damit ein späterer Abgleich es nicht als Drift meldet.

## Report-Back

**Umgesetzt wie geplant, eine Konkretisierung beim Kontrakt-Check:** `CreateCollectionRequest`
trägt keine Asset-Ids — `createAlbum()` ruft deshalb `createCollection` und danach `addItems`
nacheinander auf, nicht in einem Call (kein Plan-Abweichung, nur die vom Plan selbst geforderte
Verifikation gegen `collections.py:315`, s.o.).

Zusätzlich zur AK-Checkliste eine kleine, nicht in der Checkliste stehende Ergänzung: ein
„Abbrechen"-Button im Titel-Eingabefeld (Teil A) — die AK nennen nur „Anlegen", aber ohne
Abbruch-Weg wäre der Dialog nach dem ersten Klick auf „Album daraus anlegen" nicht mehr
zurücknehmbar. Folgt dem bestehenden Muster aus `create-person-dialog`.

Lint (`tsc --noEmit`) und `ng build` grün. Backend unangetastet — kein `ruff check` nötig.

**Nicht geprüft (Smoke, User):** Ob „Album daraus anlegen" wirklich ein sichtbares Album in der
Alben-Ansicht erzeugt und die Fehlerzeile bei einem echten Backend-Fehler brauchbar aussieht —
Plan-Smoke-Checkliste Punkt 5 deckt das ab.
