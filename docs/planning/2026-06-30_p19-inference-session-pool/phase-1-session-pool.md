# Phase 1 — SessionManager: Pool statt Singleton

**Rating:** heikel (Concurrency-Design, Kontrakt für Phase 2 wird hier festgelegt)

## Kontext (vor dem Start lesen)

- `backend/photofant/inference/session_manager.py` — komplette Datei (204 Zeilen), insbesondere
  `_SessionEntry`, `acquire_session`/`release_session` (bestehende Singleton-Cache-Logik,
  bleibt für andere Caller unverändert), `evict_idle`, `evict_all`, `shutdown`.
- `backend/photofant/inference/adapters/wd14.py` — `WD14Tagger.tag()`, Zeile 55-82: heute
  `session_manager.acquire_session(self._model_path)` / `release_session(...)`.
- `backend/photofant/inference/adapters/florence2.py` — Zeile ~119-139: vier
  `acquire_session`-Aufrufe (embed/vision/encoder/decoder-Session) für einen Caption-Lauf.
- `backend/photofant/jobs/queue.py` — Kommentarblock Zeile 88-93 (Begründung, warum getrennte
  Sessions pro Worker nötig sind) und `_tagging_worker`/`_captioning_worker` (Zeile 211-225) —
  hier läuft aktuell nur je ein Worker-Task; Phase 2 macht daraus N.
- **Nicht anfassen:** `media/ops.py`, `inference/adapters/clip.py`,
  `inference/adapters/buffalo_l.py` — die bleiben auf der alten `acquire_session`/
  `release_session`-Singleton-Semantik, weil sie je nur einen Worker haben.

## Warum das heikel ist

`session.run()` läuft heute synchron im aufrufenden Thread (via `asyncio.to_thread` aus dem
Job-Code) — nicht über den in `SessionManager._executor` liegenden eigenen Executor (der hat
aktuell keinen Aufrufer, siehe README „Bekannte, bewusst nicht angefasste Alt-Stelle"). Die
neue `acquire_exclusive_session` muss deshalb **selbst** exklusiven Zugriff erzwingen — nicht
über einen gemeinsamen Executor, sondern über einen echten Pool mit Blockierung
(`threading.Condition`, nicht `asyncio`, weil der Aufruf bereits in einem OS-Thread aus
`to_thread` läuft).

## Akzeptanzkriterien

1. `SessionManager` hat einen Pool pro `model_path` (`dict[str, list[_SessionEntry]]` o.ä.),
   getrennt von der bestehenden Singleton-`_sessions`-Struktur oder als Erweiterung derselben —
   Implementierungsdetail, solange die bestehende `acquire_session`/`release_session`-Semantik
   für die unveränderten Caller identisch bleibt (kein Verhaltensunterschied für CLIP/Buffalo-L).
2. `acquire_exclusive_session(model_path, pool_size)`: gibt eine freie Session zurück, lädt
   lazy bis zu `pool_size` Instanzen nach, blockiert (wartet), wenn alle `pool_size` Instanzen
   gerade in Benutzung sind.
3. `release_exclusive_session(model_path, session)`: gibt die konkrete Session-Instanz zurück
   in den Pool, weckt einen wartenden Aufrufer.
4. `evict_idle()`/`evict_all()`/`shutdown()` berücksichtigen beide Pools (Singleton + exklusiv) —
   kein Session-Typ wird beim Shutdown vergessen (sonst Speicherleck/hängender Prozess).
5. `WD14Tagger.tag()` und die Florence2-Adapter-Methode(n) nutzen `acquire_exclusive_session`/
   `release_exclusive_session` statt der alten Methoden. `pool_size` kommt aus
   `load_settings()["tagging_workers"]` bzw. `["captioning_workers"]` (Settings existieren erst
   ab Phase 2 — bis dahin hartcodiert `pool_size=1` als Platzhalter, in Phase 2 verdrahtet).
6. Ein absichtlich simulierter Fehlerfall (Modell-Datei fehlt) wirft weiterhin die bestehende,
   lesbare `RuntimeError` — Fehlerpfad nicht regressieren.
7. Bestehende Aufrufer (CLIP, Buffalo-L, `media/ops.py`) unverändert lauffähig — kurzer manueller
   Smoke-Test (ein Bild taggen/captionen über die UI) zeigt kein neues Fehlverhalten.

## Checkliste

- [x] `_SessionEntry`/Pool-Struktur für exklusive Sessions ergänzt (`_PoolEntry`/`_PoolState`)
- [x] `acquire_exclusive_session` implementiert (blockierend, `threading.Condition`)
- [x] `release_exclusive_session` implementiert
- [x] `evict_idle`/`evict_all`/`shutdown` decken beide Pools ab
- [x] `WD14Tagger.tag()` umgestellt
- [x] Florence2-Adapter umgestellt (alle vier Sessions: embed/vision/encoder/decoder)
- [x] ADR-017 geschrieben: `docs/decisions/017-inference-session-pool.md`
- [ ] Manueller Smoke-Test: ein Bild taggen + captionen über die bestehende UI, keine Regression
      (**vom User zu prüfen** — braucht die laufende Electron-App + echtes Bild, private-Profil
      testet keine UI selbst)

## Report-Back

Pool-Logik mit einem Wegwerf-Sanity-Skript gegen eine gefakte `_load_session` verifiziert
(nicht Teil des Repos, nur lokal ausgeführt): pool_size=2 lädt zwei getrennte Instanzen, ein
dritter Acquire blockiert nachweisbar bis zum Release und nutzt den freien Slot ohne Neu-Laden,
ein fehlgeschlagener Load wirft `RuntimeError` weiter **und** hinterlässt keinen hängenden
`pending`-Slot (Pool bleibt danach nutzbar), `evict_idle` entfernt nur freie, keine
gerade ausgeliehenen Pool-Einträge. Alle vier Checks grün.

`pool_size` ist in `WD14Tagger.tag()` und `Florence2Captioner.caption()` noch hartcodiert auf
`1` (TODO-Kommentar an Ort und Stelle) — Verdrahtung mit den Settings ist Phase 2, wie in den
Akzeptanzkriterien vorgesehen.

**Offen für den User:** Punkt 7 der Checkliste (manueller UI-Smoke-Test: ein Bild taggen +
captionen über die App) — die Session-Semantik ist für die unveränderten Aufrufer (CLIP,
Buffalo-L, `media/ops.py`) unangetastet (`acquire_session`/`release_session` nicht verändert),
trotzdem lohnt ein kurzer Klick-Test vor dem Weitergehen zu Phase 2, weil hier echte
Inferenz-Pfade umgestellt wurden.
