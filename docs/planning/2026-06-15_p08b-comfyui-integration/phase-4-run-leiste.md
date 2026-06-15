# P8b · Phase 4 — Galerie-Run-Leiste (Armed-Slots, Batch)

> Rating: **heikel** (zustandsbehaftete UI: Armed-Slots, Klick-Umleitung, Batch-Achse) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Trigger), Smoke-Checkliste
- [Konzept-ComfyUI-Integration](../../Konzept-ComfyUI-Integration.md) §3a (vollständig)
- Phase 3 (run-Endpoint, Batch-Regeln)
- Galerie-Prototyp: `docs/design/js/gallery.jsx`, `docs/design/Photofant Galerie.html`, `docs/design/styles.css` — **Run-Leiste ist neue UX, kein bestehender Prototyp**; Design-Tokens (`styles.css`) als Quelle, Look an der Galerie ausrichten.

## Akzeptanzkriterien

- **Action-Button** (Filterleiste, Wand-/Funken-Icon) aktiviert Workflow-Modus → schlanke angedockte **Run-Leiste**: Workflow-Dropdown (nur aktive valide aus Phase 2), ein Slot pro Input (Label aus `label`, Thumbnail nach Bindung), Feuer- + Reset-Button.
- **Armed-Slot-Prinzip:** Klick auf Slot armt ihn („Klicke ein Bild für: Referenz"). Solange scharf, **bindet der nächste Galerie-Klick** das Bild statt Detailansicht zu öffnen; danach entschärft. Ist kein Slot scharf, verhält sich die Galerie normal. **Esc** oder erneuter Slot-Klick entschärft.
- **Filter voll nutzbar** während des Modus (Referenz filtern → binden, Quelle filtern → binden, alles im selben Grid).
- **Wiederholen:** nach Feuern bleiben alle Bindungen erhalten; nur variablen Slot neu armen → Bild → feuern. Optional 🔒 gegen versehentliches Re-Armen (`lockable`).
- **Batch per Multi-Select:** Strg-Klick / Shift-Klick (Desktop), Long-Press (Mobile) sammelt in den scharfen Slot → Slot zur Batch-Achse, zeigt Anzahl. Einfacher Klick = Einzelbild + sofort entschärft (Schnellpfad). **Genau eine** Achse; Multi-Select in zweiten Slot **verschiebt** sie (mit Hinweis). Feuer-Button zeigt Anzahl („Feuern (12×)").
- Feuer-Button aktiv ab allen Pflicht-Slots → `POST .../run` (Phase 3). Status „an ComfyUI gesendet" + `prompt_id`(s).
- **Reset** löst alle Bindungen, verlässt den Modus, blendet die Leiste aus. Workflow-Wechsel mitten im Modus → Bindungen verwerfen (kurze Rückfrage).
- `kind = mask`: Slot öffnet den **Masken-Editor** auf dem zuvor gebundenen Quellbild — **abhängig von P9 Phase 4** (Masken-Editor). Bis dahin sind Masken-Slots in der Run-Leiste gegated mit Hinweis (siehe README Follow-up). Bild-Slots voll funktionsfähig.

## Checkliste

- [ ] Workflow-Modus-State (Signals lokal): aktiver Workflow, Slots, Bindungen, scharfer Slot, Batch-Achse
- [ ] Run-Leiste-Component (Dropdown, Slots, Feuer/Reset) nach Design-Tokens
- [ ] Klick-Umleitung im Grid (scharfer Slot bindet statt Detail), Esc/Re-Klick entschärft
- [ ] Multi-Select-Integration (Strg/Shift/Long-Press) → Batch-Achse + Anzahl, Achsen-Verschiebe-Hinweis
- [ ] Feuer-Verdrahtung an `run` (Anzahl im Button), Bindungs-Erhalt nach Feuern, 🔒
- [ ] Masken-Slot: gegated mit Hinweis (Dependency P9 Ph4) — nicht implementieren, nur sauber sperren
- [ ] Tests: Armed→bind→entschärft, Schnellpfad vs. Batch, Achsen-Verschiebung, Pflicht-Slot-Gating, Reset/Workflow-Wechsel
- [ ] Doc-Update: README-Smoke abhaken-fähig; ggf. neuen Run-Leisten-Prototyp/Screenshot unter `docs/planning/artifacts/`

## Report-Back
