# Suche — Redesign & Bugfixes

**Ausgangspunkt:** User-Feedback 2026-07-02 — kein Redirect zur Galerie beim Suchen, semantische Suche fühlt sich langsam an, globale Suchleiste liefert nach einer semantischen Suche keine Vorschläge mehr, und das Interaktionsmodell (Freitext vs. exakter Filter vs. Semantik) soll neu geschnitten werden.

**Root-Cause-Befund (vor Phase 1 schon verifiziert, kein Rätselraten mehr):**
`frontend/src/app/store/search/search.reducer.ts:19` — `setQuery` ändert nur `q`, nie `mode`. `searchActions.setMode` wird im **gesamten Frontend nirgends dispatcht** (verifiziert per Grep). Sobald einmal ein Semantik-Vorschlag gewählt wird (`search-box.ts:176-178`, setzt `mode: 'semantic'`), bleibt der Modus für den Rest der Session hängen — jede weitere Freitext-Eingabe läuft ab sofort **unbemerkt als CLIP-Embedding-Suche** statt als schnelle Tag-Filterung. Das erklärt „langsam" (jede Eingabe embedded jetzt) **und** „liefert keine Vorschläge mehr" (die Galerie zeigt Ergebnisse einer Bedeutungssuche auf Tag-Text, oft leer/falsch) in einem Aufwasch. Zusätzlich fehlt `searchActions.setSemanticQuery` in der Trigger-Liste von `gallery.effects.ts:56-73` — die Galerie reagiert auf eine gewählte Semantik-Suche gar nicht automatisch.

**Redirect-Precedent bereits im Code:** `features/personen/personen.ts:41-44` macht exakt das gewünschte Muster (`dispatch` + `router.navigate(['/galerie'])`) — wird 1:1 für die Suchleiste übernommen.

## Kontrakt (Frontend ↔ Backend)

- **`SearchMode`** (`frontend/src/app/models/asset.model.ts:1` ↔ `backend/photofant/api/assets.py:52-55`) bekommt einen vierten Wert **`'text'`** — breite Freitextsuche über Tag-Name + Caption + Personen-Name, fuzzy. Bestehende Werte (`tags`, `caption`, `semantic`) bleiben unverändert nutzbar.
- **`GET /api/assets`** (`q`, `q_mode`) bekommt den neuen Zweig `q_mode=text` in `assets.py:488-518`. Response-Form (`AssetsPage`) ändert sich nicht.
- Exakte Filter (Person, Tag) laufen **nicht** über `q`/`q_mode`, sondern über die bestehenden `filtersActions.setPersonId` / `filtersActions.setTagIds` (keine neue Route nötig).
- `POST /api/search/semantic` (`api/search.py`, `docs/routes.md:486`) bleibt unangetastet — verifiziert toter Code (kein Frontend-Aufrufer), wird in diesem Plan **nicht** entfernt (kein Auftrag dazu), aber die Doku-Diskrepanz in `routes.md` wird in Phase 1 korrigiert.

## Phasen

| # | Phase | Tier | Status |
|---|---|---|---|
| 1 | [Bugfixes: hängender Modus, fehlender Redirect, fehlendes Reset](phase-1-bugfixes-redirect.md) | standard | complete |
| 2 | [Interaktionsmodell: Dropdown/Freitext-Fuzzy/exakte Auswahl](phase-2-interaktionsmodell-fuzzy.md) | heikel | complete |
| 3 | [Semantische Suche: Kaltstart-Latenz beheben](phase-3-semantic-performance.md) | standard | complete |

## Finale Abnahmekriterien (Smoke, macht der User am Ende)

1. Auf einer beliebigen Nicht-Galerie-Seite in die Suchleiste tippen → Galerie öffnet sich automatisch, gefiltert.
2. Klick in die leere Suchleiste → Dropdown zeigt Suchverlauf.
3. Tippen (z. B. Teil eines Tag-Namens, eines Personennamens oder eines Caption-Worts, auch mit einem Tippfehler) → Galerie filtert live (debounced), Dropdown zeigt passende Personen/Tags + einen Semantik-Eintrag.
4. Pfeiltasten/Maus wählen Person → Galerie filtert exakt auf diese Person (kein Fuzzy-Rest-Treffer).
5. Pfeiltasten/Maus wählen Tag → Galerie filtert exakt auf diesen Tag.
6. Pfeiltasten/Maus wählen Semantik-Eintrag → CLIP-Suche läuft, Galerie zeigt Ähnlichkeits-Ergebnisse.
7. Direkt danach normalen Text tippen → läuft wieder als schnelle Freitextsuche, **nicht** mehr als Semantik-Suche (Regressionstest für den Root-Cause-Bug).
8. Semantik-Suche fühlt sich spürbar schneller an als vorher (subjektive Abnahme + grobe ms-Angabe aus Phase 3).

## Follow-ups (nicht Teil dieses Plans)

- `POST /api/search/semantic` ist toter Code — Entscheidung „entfernen oder für „ähnliche Bilder" reaktivieren" liegt außerhalb dieses Scopes.

## Summary

Suchleiste redirectet jetzt automatisch zur Galerie, der hängende Semantik-Modus-Bug ist behoben
(Root Cause: `setQuery` änderte nie den Modus zurück), Freitext läuft standardmäßig fuzzy über
Tag/Caption/Personen-Namen, exakte Auswahl (Person/Tag) läuft über die bestehenden Filter-Actions,
und die semantische Suche hat keinen spürbaren Kaltstart mehr (Prewarm senkt effektive Latenz von
~9.4s auf ~18ms bei der ersten Suche nach Inaktivität).

## Files touched

- `frontend/src/app/store/search/` (Reducer/Actions/Effects — Modus-Reset, Redirect)
- `frontend/src/app/ui/search-box/` (Dropdown, Fuzzy-Freitext, Prewarm-Trigger)
- `frontend/src/app/services/search.service.ts` (neu)
- `frontend/src/app/store/gallery/gallery.effects.ts` (Trigger-Liste erweitert)
- `backend/photofant/api/assets.py` (`q_mode=text`, Fuzzy-Scoring)
- `backend/photofant/api/search.py` (`POST /api/search/warm`, neu)
- `backend/photofant/inference/adapters/clip.py` (`warm_text()`, neu)
- `docs/routes.md`, `docs/code-map.md`

## Commits

- Plan angelegt — `a4d2c9b`
- Phase 1 (Bugfixes: Modus-Fix, Redirect) — `1aafe6b`
- Phase 2 (Interaktionsmodell/Fuzzy) — `86715f1`
- Phase 3 (Kaltstart-Prewarm) — `b96f97b`

## Deviations

Keine — Umsetzung folgt dem Kontrakt und den Phasen-Checklisten 1:1. `docs/clients.md` existiert in
diesem Projekt nicht (Frontend-Aufrufer stehen inline in `routes.md`) — dort dokumentiert statt einer
neuen Datei.
