# P26 — Recommendation Engine

> Roadmap-Phase 5 (Dok 050 §6/§10, Dok 030 §5). Kontextbezogene Empfehlungen mit nachvollziehbarer Begründung. Baut auf **P22** + **P25** auf. **Kein neues Modell** — kombiniert vorhandene Bild-CLIP-Ähnlichkeit mit dem Wissensgraph. *(private, lean.)*

## Ziel
Unter dem Lore Panel erscheinen Empfehlungen: Vorschaubild, Score, Begründungskette („✓ gleiche Person · ✓ gleiche Rolle · ✓ CLIP 0.94"). Der Nutzer sieht „Warum empfohlen?" und „Warum nicht?".

## Scope
**Drin:** `RecommendationJob` = CLIP-Bildähnlichkeit (`db/vector_index.py`, `inference/adapters/clip.py`) + Graph-Signale (gleiche Person/Rolle/Film über P22-Relationships) → Score + Reason-Chain · `RecommendationUpdateJob` + `recommendation_cache` · Karten-UI unter dem Lore Panel · Explainability „Warum?/Warum nicht?" (auch rückwirkend für P25-Korrekturen).
**Draußen:** KI-Empfehlungstexte → später · Discovery/Sammlungsanalyse → Roadmap-Phase 8 (eigener Plan).

## Abhängigkeiten
**P22** (Graph/Relationships, Service) + **P25** (Lore Panel als Andockort, Explainability-Grundlage). Nutzt **Bestand**: CLIP-Embeddings + `sqlite-vec` (`db/vector_index.py`), Person-Zuordnung — kein neuer ML-Pfad.

## Kontrakt-Ergänzungen
- **`recommendation_cache`** (eigene Migration): `source_asset_id`, `recommended_asset_id`, `score`, `reasons` (JSON: [{signal, detail, weight}]), `computed_at`. Cache, neu erzeugbar.
- **Job:** `jobs/recommendation_job.py` → `RecommendationJob(source_asset_id)`: Kandidaten aus CLIP-Nachbarn + graph-verbundenen Assets, gewichteter Score, Reason-Chain. Idempotent, Depth-Schutz.
- **REST:** `GET /api/recommendations?asset_id=` (aus Cache; fehlt → Job planen, leere Liste + „wird berechnet") · `GET .../{source}/{target}/why-not`.
- **Explainability-Payload** (geteilt mit P25): `{ model?, capability?, reasons[], confidence, job }` (Dok 040 §12).

## Reservierte Entscheidungen & Settings
- **ADR-012** — Empfehlungen ohne neuen Vektorstore: Wiederverwendung Bild-CLIP + Graph, Reason-Chain aus gewichteten Signalen. `docs/decisions/012-recommendation-reason-chain.md`.
- **settings.json (vorab freigeben):** `recommendations.maxResults` (12) · `recommendations.minScore` (0.3) · `recommendations.weights` (samePerson/sameRole/sameFilm/clipSimilarity — tunebar) · `recommendations.enabled` (bool, ADR-008).

## Design-Lage (freihändig — freigegeben)
Kein Mockup. Karte = Vorschaubild + Score + Reason-Checkliste (Dok 050 §6). Dockt unter P25s Panel — **Screen-Eigentümer:** Lightbox=P15, Panel=P25; P26 fügt sich darunter ein.

## Phasen
| # | Phase | Komplexität | Status |
|---|---|---|---|
| 1 | Recommendation-Job + Reason-Chain (Backend) | heikel (Scoring/Gewichtung) | **complete** |
| 2 | Empfehlungs-Karten-UI (unter Lore Panel) | standard | **complete** |
| 3 | Explainability „Warum?/Warum nicht?" | standard | pending |

## Finale AK (Gesamt)
- [ ] Zu einem Bild erscheinen unter dem Lore Panel Empfehlungen mit Vorschaubild, Score, Begründungskette aus konkreten Signalen (Person/Rolle/Film + CLIP-Wert).
- [ ] Empfehlungen kombinieren nachweisbar Bild-Ähnlichkeit **und** Graph (nicht nur CLIP) — an einem Beispiel belegbar.
- [ ] „Warum?" zu jeder Empfehlung + „Warum nicht?" zu einem nicht empfohlenen Bild abrufbar.
- [ ] Über Schwellwert + Gewichte konfigurierbar, abschaltbar.
- [ ] Kein neuer Modell-Download, keine Laufzeit-Netzwerkzugriffe.

## Smoke-Checkliste (du prüfst am Plan-Ende)
1. `curl GET /api/recommendations?asset_id=<x>` → ≥1 Empfehlung mit gemischter Reason-Chain (CLIP + Graph-Signal sichtbar).
2. Bild öffnen → Karten unter dem Panel mit Score + ✓-Begründungen; Karte klicken → Bild öffnet.
3. „Warum?"-Popover zeigt Signale/Confidence/Job; „Warum nicht?" an einem anderen Bild erklärt fehlende Signale.
4. `recommendations.enabled=false` → keine Empfehlungen.

## Risiken
- 🟡 **Scoring-Qualität** (falsche Gewichte = wertlose Empfehlungen) → Gewichte in settings, an realem Set kalibrieren, Reason-Chain macht Fehlgewichtung sichtbar. **Der Kern-Punkt.**
- 🟡 **Performance bei großer Bibliothek** → Cache + Job (nicht synchron in der API), `maxResults`-Deckel, CLIP-Vorfilter.
- 🟡 **„Warum nicht?" teuer** → nur auf Anfrage berechnen, Signale gegen Schwellwert erklären.

## Chesterton
**Vor Nutzung verstehen:** die Vektorsuche (`db/vector_index.py`, `inference/adapters/clip.py`, `api/search.py`) liefert bereits CLIP-Nachbarn. P26 **liest** daraus, ändert den Suchpfad nicht. Andockort unter P25s Panel — dessen Struktur nicht umbauen.

---
## Summary / Deviations / Follow-ups
_(beim Archivieren)_ — Follow-ups: Discovery/Sammlungsanalyse (Roadmap-Phase 8) · KI-Empfehlungstexte.
