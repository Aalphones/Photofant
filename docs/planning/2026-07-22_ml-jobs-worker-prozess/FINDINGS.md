# Findings — Worker-Prozess für ML-Inferenz-Jobs

Getaggte Erkenntnisse aus der Umsetzung, die eine spätere Phase betreffen. Format:
`- [ ] → Phase N: <Erkenntnis>`. Wird von `mode-implementing` gepflegt.

- [ ] → Phase 2: Konfidenz-Ausweis-Punkt 2 (SQLite aus zwei echten Prozessen) konnte in Phase 1
      nicht geprüft werden — der DEMO-Job rührt die DB nicht an. Sobald CAPTIONING/TAGGING im
      Worker laufen, den Check nachholen: parallel aus API- und Worker-Prozess lesen/schreiben,
      auf `database is locked` prüfen (README „Konfidenz-Ausweis" Punkt 2).
