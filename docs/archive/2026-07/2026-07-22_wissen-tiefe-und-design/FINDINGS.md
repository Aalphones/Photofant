# Findings

Erkenntnisse aus der Umsetzung, die eine spätere Phase betreffen. Format:

```
- [ ] → Phase N: <Erkenntnis>
```

Erledigt = abgehakt, mit einem Halbsatz, wie es aufgelöst wurde.

---

- [x] → Phase 3: Der Interview-Vorschlag trägt jetzt `suggestion.attributes` (Key →
  `{label, value, owner, confidence}`, Label reist mit). Das Frontend-Model
  `KnowledgeInterviewSuggestion` kennt das Feld **noch nicht** — es muss in Phase 3 dazu,
  zusammen mit der Anzeige in der Zusammenfassung und `CreateEntityRequest.attributes`.
  Erledigt: `InterviewAttributeDto` + Feld ergänzt, Anzeige + `onConfirm()`-Übernahme gebaut.
- [x] → Phase 3: Owner-Pills brauchen zwei Fälle aus dem Interview: `user` = „Selbst
  angegeben" (Confidence 1.0), `inferred` = „KI-Schätzung" (Confidence aus dem Modell,
  Fallback 0.5 wenn es keine mitliefert). Erledigt: `ivOwnerLabel()`/`ivOwnerClass()` im
  Interview-Dialog, eigene Pill-Farben in `interview-dialog.scss`.
