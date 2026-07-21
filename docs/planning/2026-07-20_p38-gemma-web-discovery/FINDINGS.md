# Findings — P38 Wissen: Web-Recherche + neue Oberfläche

Getaggte Erkenntnisse aus der Umsetzung, die eine spätere Phase betreffen. Format:
`- [ ] → Phase N: <Erkenntnis>`. Wird von `mode-implementing` gepflegt.

- [ ] → Phase 3: `ddgs` 9.14.4 liefert die Keys `title` / `href` / `body` — genau die Form, die
  `search_web()` erwartet; keine Anpassung nötig. Ein Treffer ohne `href` wird verworfen, die
  Liste kann also kürzer sein als `max_results`. Der Job muss den Fall „0 Treffer" tragen
  (kein Fehler, sondern leere Fakten-Liste).
- [ ] → Phase 4: `autonomy_for()` fällt bei einem **unbekannten** Autonomie-Key auf `"ask"`
  zurück, nicht auf `"off"`. Für `discovery` greift das nie, weil `load_settings()` die
  Defaults tief einmischt — aber die Route muss trotzdem auf `!= "auto"` gaten (so geplant),
  nicht auf `== "off"`, sonst wäre `"ask"` versehentlich durchlässig.
