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
| 2 | [Interaktionsmodell: Dropdown/Freitext-Fuzzy/exakte Auswahl](phase-2-interaktionsmodell-fuzzy.md) | heikel | pending |
| 3 | [Semantische Suche: Kaltstart-Latenz beheben](phase-3-semantic-performance.md) | standard | pending |

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
