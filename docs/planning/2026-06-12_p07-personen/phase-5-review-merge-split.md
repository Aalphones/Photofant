# P7 · Phase 5 — Review-Queue, Merge & Split

> Rating: **heikel** (Merge verschiebt ganze Bestände physisch; falsch herum gemergt tut weh) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (review-queue, merge, split)
- [Konzept](../../Konzept-Photofant.md) §7 (Review-Queue, Merge/Splitten, Top-Matches mit Score-Anzeige)
- `docs/design/js/review.jsx` (Review-Layout)

## Akzeptanzkriterien

- Review-Queue-View nach Prototyp (Sidebar mit Items, großes Bild, Aktionspanel, Progress): bestätigen → Move zur vorgeschlagenen Person; ablehnen → `_unknown`; Score sichtbar als %.
- Merge: Auswahl zweier Personen (UI zeigt beide Avatare + Counts zur Verwechslungs-Bremse, Bestätigungs-Dialog mit Klartext „X Bilder wandern von A nach B"), physisches Verschieben über die Phase-3-Orchestrierung, Embeddings/Cluster umgehängt.
- Split: Faces einer Person markieren → neue Person mit physischem Umzug der zugehörigen Instanzen.
- Top-10-Matches-Ansicht für ein Face (disjunkte Personen, Score-%) als Korrektur-Einstieg im Detail-Panel.

## Checkliste

- [ ] Review-Queue-Persistenz (Score-Band aus Phase 2) + Endpoints + View
- [ ] Merge-Endpoint + Bestätigungs-UI (Richtungs-Klarheit!)
- [ ] Split-Flow (Face-Auswahl in der Personen-Detail-Ansicht)
- [ ] Matches-Panel (Detail-Panel-Sektion „Person zuweisen" mit Top-10 + Score)
- [ ] Tests: Merge-Konsistenz (Datei-Count, keine Verluste), Split-Zuordnung
- [ ] Doc-Update: routes.md

## Report-Back
