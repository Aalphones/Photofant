# Phase 2 — Settings + N-Worker-Loop in queue.py

**Rating:** standard (Kontrakt aus Phase 1 ist klar, normale Verdrahtungsarbeit)

## Kontext (vor dem Start lesen)

- `backend/photofant/settings.py` — `SETTINGS_DEFAULTS`-Dict (Zeile ~64-108) und
  `_EXPECTED_TYPES`-Dict (Zeile 110-141). Kein Range-Clamping auf Backend-Seite bei bestehenden
  Slidern (z.B. `face_auto_threshold`) — Clamping passiert clientseitig (Phase 4). Hier nur
  Typ-Validierung ergänzen.
- `backend/photofant/jobs/queue.py` — `JobQueue.__init__` (Zeile 102-116, Task-Handles),
  `start()` (117-124), `stop()` (126-141), `_tagging_worker`/`_captioning_worker` (211-225).
  Aktuell je ein `asyncio.Task`-Handle pro Typ — wird zu einer Liste von Tasks.
- `docs/code-map.md` Zeile 65 — beschreibt die Queue aktuell mit „drei Spuren"; das ist bereits
  vor P19 unvollständig (dedizierte Tagging/Captioning-Worker fehlen in der Beschreibung) und
  muss hier ohnehin korrigiert werden, weil sich die Spuren-Anzahl durch N-Worker-pro-Typ ändert.
- Phase-1-Kontrakt: `SessionManager.acquire_exclusive_session(model_path, pool_size)` erwartet
  `pool_size` — diese Phase liefert den echten Wert aus den Settings statt des Platzhalters `1`.

## Akzeptanzkriterien

1. `settings.json` kennt `tagging_workers` (Default `1`) und `captioning_workers` (Default `1`),
   inkl. Typ-Validierung in `_EXPECTED_TYPES` (beide `int`).
2. `JobQueue.start()` startet `settings["tagging_workers"]` Tagging-Worker-Tasks und
   `settings["captioning_workers"]` Captioning-Worker-Tasks (alle lesen von derselben
   `_tagging_queue`/`_captioning_queue` — FIFO über alle Worker eines Typs hinweg).
3. `JobQueue.stop()` cancelt **alle** gestarteten Worker-Tasks eines Typs, nicht nur den ersten
   (sonst hängende Tasks beim Shutdown).
4. `WD14Tagger`/Florence2-Adapter (Phase 1) übergeben den echten Settings-Wert als `pool_size`
   an `acquire_exclusive_session` — kein hartcodierter Platzhalter mehr.
5. Mit `tagging_workers=1` (Default) ist das Verhalten **exakt identisch** zu heute — Regression
   für den Standardfall ausgeschlossen.
6. `docs/code-map.md` Zeile 65 beschreibt die Queue korrekt: Tagging- und Captioning-Worker sind
   je in konfigurierbarer Anzahl (Settings) vorhanden, nicht mehr fix „ein Worker".

## Checkliste

- [ ] `tagging_workers`/`captioning_workers` in `SETTINGS_DEFAULTS` + `_EXPECTED_TYPES`
- [ ] `JobQueue`: Task-Handles von Einzel-Task auf `list[asyncio.Task]` pro Typ umgestellt
- [ ] `start()`: liest Settings, startet N Tasks pro Typ
- [ ] `stop()`: cancelt alle Tasks der Liste
- [ ] WD14/Florence2-Adapter (aus Phase 1) an echten Settings-Wert angebunden
- [ ] Manueller Test: `tagging_workers=1` (Default) — Verhalten unverändert
- [ ] Manueller Test: `tagging_workers=2`, Batch-Import mit mehreren Bildern → zwei TAGGING-Jobs
      laufen im Job-Dock sichtbar überlappend
- [ ] `docs/code-map.md` Zeile 65 aktualisiert

## Report-Back
