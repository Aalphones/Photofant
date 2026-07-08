# Phase 4 — Text-Semantiksuche verdrahten

**Komplexität:** standard · **Status:** done

## Kontext (vor dem Bauen lesen)
- `backend/photofant/api/search.py` — `semantic_search` mit `query` (Text→Bild, existiert, embeddet via
  `embed_text`). **Kein Backend-Umbau nötig** — nur Frontend-Anbindung. (Der Endpoint braucht P35s
  `resolve_image_embedder()` im Text-Pfad — bereits Teil von P35.)
- `frontend/src/app/ui/search-box/` — die globale Suchbox (heute exakte Tag-/Caption-Suche, `q_mode=text`).
- `frontend/src/app/store/search/`, `store/filters/` — der Reverse-/Ähnlichkeits-Filtermodus aus Phase 1/2
  (geordnete `similar_ids`) wird für die Text-Treffer wiederverwendet.
- `backend/photofant/api/assets.py` — `list_assets(similar_ids=…)` aus Phase 1.

## Warum das fast geschenkt ist
Der Text-Pfad des `/semantic`-Endpoints ist gebaut, aber hatte nie einen Frontend-Aufrufer (toter Code).
SigLIP2s mehrsprachiger Text-Encoder (P35) macht ihn brauchbar. Die Treffer sind wieder eine geordnete
id-Liste → **derselbe** Ordered-Filter-Mechanismus wie bei der Reverse-Bildsuche.

## AK der Phase
- [x] In der Suchbox ein klar beschrifteter Umschalter/Modus „semantische Suche" (neben der exakten
      Tag-/Caption-Suche) — mit Tooltip, was er tut („nach Bildinhalt suchen, nicht nach Tag-Text").
      Idiotensicherheit: der Unterschied exakt ↔ semantisch ist ohne Erklärung erkennbar.
- [x] Freitext im Semantik-Modus → thematisch passende Treffer in der Galerie, geordnet nach
      Ähnlichkeits-Score. **Abweichung vom Plan:** nicht über `POST /api/search/semantic` +
      `similar_ids`-Filter, sondern über den bereits bestehenden `q_mode=semantic`-Pfad in
      `list_assets` — Details + Begründung siehe Report-Back unten und `docs/routes.md`
      („Semantische Suche").
- [x] 409 `SEMANTIC_SEARCH_UNAVAILABLE` (kein Embedder aktiv) zeigt eine klare deutsche Meldung.
- [x] Chip/Anzeige macht klar, dass ein Semantik-Ergebnis aktiv ist; Zurücksetzen wie bei den anderen Filtern.
- [x] `npm run lint` + `npm run build` grün.

## Doc-Updates
- [x] `docs/routes.md` — Abschnitt „Semantische Suche" um die Entscheidung gegen den Umbau auf
      `POST /api/search/semantic` ergänzt; Route-Tabelle korrigiert (`like_asset_id`-Zweig hat seit
      Phase 3 einen Frontend-Aufrufer, war noch als „kein Frontend-Aufrufer" dokumentiert); die
      „Bekannte Überschneidung"-Notiz zu `/assets/{id}/similar` als entschieden markiert (war seit
      Phase 3 fällig, aber nicht nachgezogen).
- [x] `docs/code-map.md` — Suche-Zeile: expliziter Umschalter, `api-error.util.ts`, Galerie-Fehler-Toast.

## Report-Back

**Abweichung vom Plan (Architektur-Entscheidung, mit dem User abgestimmt 2026-07-08):**
Der Plan sah vor, den Text-Pfad über `POST /api/search/semantic {query}` zu führen und die Treffer
als `similar_ids`-Ordered-Filter (Wiederverwendung der Reverse-Search-Mechanik aus Phase 1–3) in die
Galerie zu laden. Bei der Umsetzung fiel auf: dieser Endpoint-Zweig war zwar tatsächlich ohne
Frontend-Aufrufer, aber die Text-Semantiksuche selbst war es **nicht** — sie lief längst über einen
älteren, unabhängigen Pfad (`GET /api/assets?q=&q_mode=semantic`, seit P28 an die Suchbox
angeschlossen, dokumentiert in `docs/routes.md`). Dieser alte Pfad ist dem Plan-Vorschlag technisch
überlegen: volle serverseitige Paginierung/Facetten, bis zu 200 Kandidaten (statt max. 100 über
`SemanticSearchRequest.limit`), kein zusätzlicher Roundtrip. Dem User zur Entscheidung vorgelegt
(zwei Optionen, siehe Chat) — Ergebnis: alten Pfad behalten, nur die fehlenden UI-Teile nachziehen
(Umschalter, Fehlermeldung). Der `query`-Zweig von `POST /api/search/semantic` bleibt damit
weiterhin totes Backend-Duplikat (unverändert seit vorher, kein Auftrag zum Entfernen).

**Gebaut:**
- `search-box.ts`/`.html`/`.scss` — expliziter Umschalter-Button (Icon `sparkle`, Tooltip, aktiver
  Zustand farblich hervorgehoben). Store-Suchmodus (`store/search`) ist die Quelle der Wahrheit für
  den Anzeigezustand, ein lokales `pendingSemanticToggle`-Signal überbrückt nur die Lücke „Umschalter
  geklickt, aber noch kein Text getippt". Dadurch bleibt der Umschalter automatisch synchron, auch
  wenn die Suche von anderswo zurückgesetzt wird (z. B. Filter-Chip in der Sub-Toolbar).
- Die bisherige implizite „Semantisch"-Autocomplete-Zeile (letzter Dropdown-Eintrag bei jeder
  Texteingabe) wurde entfernt — der Umschalter ist jetzt der einzige Weg, eine **neue** Semantiksuche
  zu starten. Alte, per Verlaufsliste gespeicherte Semantik-Suchen bleiben weiterhin anklickbar.
- `services/api-error.util.ts` (neu) — `extractApiErrorMessage()`, geteilter Parser für die
  strukturierten Backend-Fehler (`{ detail: { code, message } }`). War vorher dreimal fast identisch
  dupliziert (`search-box.ts`, `lightbox.ts`, jetzt zusätzlich `gallery.effects.ts`) — auf den
  gemeinsamen Helper umgestellt.
- `gallery.effects.ts` — Asset-Fetch-Fehler laufen jetzt durch `extractApiErrorMessage` (deutsche
  Meldung bei 409 SEMANTIC_SEARCH_UNAVAILABLE statt generischem HTTP-Fehlertext).
- `galerie.ts`/`galerie.html` — Galerie-Ladefehler wurden bisher **nirgends angezeigt** (Store-Feld
  `error` existierte, aber keine Konsumenten-Stelle) — jetzt über den vorhandenen `runToast`-
  Mechanismus sichtbar.

**Konfidenz:** mittel-hoch. Kernstück (Umschalter-Signal-Design mit Store als Quelle der Wahrheit)
manuell durchgespielt (Toggle vor/nach Texteingabe, Chip-Entfernen von außen, Wechsel zu Tag-Filtern)
— nicht automatisiert getestet (keine Unit-Tests im Scope, private/lean-Profil). Wackelstelle für den
Smoke-Test: siehe Prüf-Checkliste unten.

**Smoke-Checkliste (zusätzlich zur Plan-Checkliste):**
1. Umschalter klicken **ohne** Text, dann tippen → landet im Semantik-Modus (nicht erst nach zweitem Tastendruck).
2. Semantik-Chip in der Sub-Toolbar über das „x" entfernen → Umschalter-Button zeigt wieder „aus" (nicht mehr lila).
3. Bild-Embedder in den Einstellungen deaktivieren (falls möglich) oder Backend kurz ohne aktiven
   Embedder starten → Semantiksuche auslösen → deutsche Fehlermeldung als Toast in der Galerie.
