# Phase 3 — Semantische Suche: Kaltstart-Latenz beheben

**Komplexität:** standard · **Status:** pending

**Voraussetzung:** Phase 1 (sonst läuft weiterhin *jede* Eingabe als Semantik-Suche und diese Phase optimiert das falsche Problem).

## Kontext (vor dem Bauen lesen)

- `backend/photofant/inference/session_manager.py` — `IDLE_TIMEOUT_SECONDS = 300` (Zeile 23), `acquire_session`/`evict_idle` (Zeile 47-95). Sessions ohne aktive Nutzung werden nach 5 Minuten evictet und beim nächsten Aufruf neu von der Platte geladen (Kaltstart).
- `backend/photofant/inference/adapters/clip.py` — `embed_text()` (Zeile 106-125), holt sich die Session über `session_manager.acquire_session`.
- `backend/photofant/api/assets.py:359-369` — `_embed_semantic`, der Aufrufpfad, der nach Phase 1 nur noch bei **expliziter** Semantik-Auswahl läuft (nicht mehr bei jedem Tastendruck).

**Einordnung:** Mit dem Phase-1-Fix läuft die teure CLIP-Suche nur noch, wenn der User sie explizit auswählt — das nimmt dem „langsam"-Problem schon den Großteil der Wucht (vorher: jede Eingabe nach einer Semantik-Suche war eine Embedding-Anfrage). Diese Phase behebt den verbleibenden Rest: den Kaltstart nach 5 Minuten Inaktivität.

## Akzeptanzkriterien

- Gemessene Latenz (grobe ms-Angabe, Server-Log oder Timing im Report-Back) für eine explizite Semantik-Suche **nach** > 5 Minuten Inaktivität ist deutlich niedriger als vorher (Vorher/Nachher-Zahl dokumentieren, kein exaktes Ziel-SLA nötig).
- VRAM-Verhalten bleibt kontrolliert — keine dauerhafte Reservierung, die mit Captioner/Generativ-Modellen kollidiert (siehe `session_manager`-Zweck: genau dafür existiert die Idle-Eviction).

## Umsetzung

- [ ] Ist-Latenz messen: einmal kalt (>5 min Pause), einmal warm — Zahlen im Report-Back festhalten, bevor optimiert wird (Spec-first-Grundsatz: erst Beleg, dann Fix).
- [ ] Prewarm-Trigger einbauen: sobald die Freitext-Eingabe im Dropdown einen Semantik-Vorschlag anzeigt (also sobald `query` nicht leer ist, siehe `search-box.ts:99`), im Hintergrund einen leichten Aufruf absetzen, der `resolve_clip_embedder()` + Text-Session anstößt, **ohne** auf das Ergebnis zu warten oder einen Suchtreffer zu erzeugen — Ziel: Session ist bereits warm, wenn der User tatsächlich auswählt. Braucht einen kleinen neuen Endpunkt oder Wiederverwendung eines bestehenden (prüfen, ob `api/models.py` bereits einen Warm-Mechanismus für andere Adapter hat, sonst neu in `api/search.py` — Namensschema beachten).
- [ ] Debounce für den Prewarm-Call großzügiger wählen als der Suggestion-Debounce (z. B. 500-800 ms), damit nicht jeder Tastendruck einen Warm-Request auslöst.
- [ ] Doc: `docs/routes.md` (neuer Endpunkt, falls angelegt), `docs/clients.md` (neue Service-Methode, falls Frontend-seitig ein Client-Call dazukommt).

## Report-Back
