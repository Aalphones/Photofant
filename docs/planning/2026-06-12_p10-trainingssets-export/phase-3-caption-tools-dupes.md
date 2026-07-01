# P10 · Phase 3 — Caption-Tools & Near-Dupes

> Rating: standard · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (captions-Action, duplicates)
- [Konzept](../../Konzept-Photofant.md) §9 (Caption-Tools, Near-Dupe-Vergleich)
- `docs/design/js/compare.jsx` (Links-Rechts-Vergleich)

## Akzeptanzkriterien

- Set-weite Caption-Aktionen: Trigger-Word voranstellen, Prefix/Suffix anhängen, Find-Replace — wirken auf `caption_override` (Original-Captions der Galerie bleiben unberührt), mit Vorher/Nachher-Vorschau (Stichprobe) vor dem Ausführen.
- Near-Dupe-Endpoint (pHash-Paare im Set, Schwelle einstellbar) + Links-Rechts-Review-UI: pro Paar links/rechts/beide behalten; Verworfene → Papierkorb (P2-Strecke).
- Beide Strecken über die Queue (große Sets), Fortschritt sichtbar.

## Checkliste

- [x] captions-Action-Endpoint (4 Aktionen, idempotent formuliert: Trigger-Word nicht doppelt voranstellen)
- [x] Vorschau-Dialog (5 Beispiel-Captions vorher/nachher)
- [x] Dupe-Paar-Endpoint + Review-UI (Vergleich, Tastatur: ←/→/B)
- [x] Doc-Update: routes.md

## Report-Back

**Backend:** `photofant/collections/captions.py` (reine Transform-Funktion, idempotent für alle drei Text-Aktionen, nicht nur Trigger-Word) · `photofant/jobs/captions_job.py` (Queue-Job) · `JobKind.CAPTIONS` in `jobs/queue.py` · drei neue Routen in `api/collections.py` (`POST /captions`, `GET /duplicates`, `POST /duplicates/resolve`).

**Frontend:** `training-set-captions/` (Modal: 4 Aktionen, Live-Vorschau ohne Server-Roundtrip — TS-Spiegel der Backend-Transform) · `training-set-dupes/` (Seiten-Panel: Schwelle einstellbar, Paarliste, Vergleichs-Overlay mit ←/→/B) · beide neu verdrahtet in `trainingssets.ts`/`.html` (Toolbar-Buttons „Caption-Tools" und Near-Dupe-Icon).

**Deviations vom Plan:**
1. Keine separate Preview-Route — die 5-Beispiel-Vorschau läuft rein clientseitig gegen die bereits geladenen Set-Items (kein Server-Roundtrip nötig, Konzept-Routenliste kennt ohnehin nur `POST /captions`).
2. `GET /duplicates` ist **live berechnet** (kein persistierter Review-Queue-Eintrag wie beim bibliotheksweiten Dupe-Scan) — gleiche Begründung wie `compute_training_set_stats` (Set-Größe bis niedrige Hunderte, O(n²) unter einer Sekunde).
3. `keep_both` ist **nicht persistiert** — reines Client-Dismiss für die aktuelle Panel-Session. Öffnet der User das Panel neu, kann ein zuvor "beide behalten"-entschiedenes Paar erneut auftauchen. Eine dauerhafte Markierung hätte eine Schema-Migration gebraucht (kein Feld dafür auf `collection_item`); für Trainingsset-Größenordnungen als vertretbar bewertet.
