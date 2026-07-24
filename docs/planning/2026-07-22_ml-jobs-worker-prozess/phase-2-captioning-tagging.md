# Phase 2 — Erstmigration: Captioning + Tagging

**Komplexität:** heikel (erster echter Modell-Job im Worker, erste Cross-Process-Pipeline-Signalisierung).

## Kontext (lesen vor dem Start)

- [backend/photofant/jobs/caption_job.py](../../../backend/photofant/jobs/caption_job.py) —
  `run_caption_job`, `enqueue_caption`. Payload heute schon minimal: `asset_id`.
- `backend/photofant/jobs/tagging_job.py` — analoges Muster, gegenchecken, ob der Payload
  ebenso schlank ist oder zusätzliche Objekte durchreicht (Risiko README Punkt „Payload-Umbau").
- [backend/photofant/jobs/face_pipeline.py](../../../backend/photofant/jobs/face_pipeline.py) —
  `signal()` wird heute am Ende von `_run_caption_with_preset` (im `finally`) und am Ende der
  Tagging-Ausführung aufgerufen. Nach dieser Phase laufen beide Aufrufer im Worker-Prozess —
  `face_pipeline` selbst bleibt aber im API-Prozess (Entscheidung README „Wichtige Funde").
- `backend/photofant/inference/session_manager.py` — der ONNX-Session-Pool, den Florence-2 (und
  WD14 für Tagging) nutzen. Zieht unverändert in den Worker um, nur der Aufrufkontext ändert sich.
- Phase-1-Ergebnis: `worker/protocol.py`, `worker/process.py`, `worker/dispatch.py`,
  `JobQueue._REMOTE_KINDS`/Remote-Enqueue-Pfad. Diese Phase erweitert alle drei, baut nichts neu.

## Aufgabe 1 — Payload-Umbau: Captioning

`enqueue_caption()` in `caption_job.py` ändert sich von einem lokalen `coro_factory`-Enqueue auf
den Remote-Pfad aus Phase 1 (`enqueue_remote`/erweiterter `enqueue()`, je nachdem wie Phase 1 das
benannt hat): Payload `{"asset_id": asset_id}`. `run_caption_job` selbst (die Funktion, die heute
`await asyncio.to_thread(_run_caption, asset_id)` macht) bleibt unverändert — sie läuft jetzt nur
im Worker-Prozess statt im API-Prozess. `JobKind.CAPTIONING` wandert in `_REMOTE_KINDS`.

Dispatch-Tabelle (`worker/dispatch.py`) bekommt die Zeile:
```python
JobKind.CAPTIONING: lambda status, payload: run_caption_job(status, payload["asset_id"]),
```
(Der `override_preset_id`/`force`-Pfad aus `_run_caption_with_preset` hat heute keinen
Frontend-Caller über `enqueue_caption` — prüfen, ob `rerun_job.py` das nutzt und ggf. den Payload
entsprechend erweitern statt zu kappen.)

## Aufgabe 2 — Payload-Umbau: Tagging

Analog zu Aufgabe 1, für `tagging_job.py`. Gegenchecken (siehe Kontext), ob der Payload wirklich
nur `asset_id` braucht — falls nicht, hier die erste Stelle, an der ein Job mehr als eine Skalar-ID
durchreicht, und das Muster für alle Fälle in Phase 3 festlegen (z.B. verschachtelte, aber
JSON-simple Dicts sind erlaubt — ORM-Objekte nicht).

## Aufgabe 3 — Cross-Process-Signalisierung für FACE

Das ist der riskanteste Teil dieser Phase (Konfidenz-Ausweis README Punkt 1). Heute ruft
`_run_caption_with_preset` (im Worker-Thread, bald im Worker-**Prozess**) am Ende
`face_pipeline.signal(asset_id)` auf — das geht nicht mehr direkt, `face_pipeline` lebt im
API-Prozess.

Lösung (README „Kontrakt"): statt `face_pipeline.signal(asset_id)` direkt zu rufen, schreibt der
Worker eine `PipelineSignalMessage(type="pipeline_signal", pipeline="face", asset_id=asset_id)`
auf die Status-Queue (denselben Kanal wie `JobStatusMessage`, mit `type` als Unterscheidungs-Feld
— der API-seitige Status-Forwarder aus Phase 1 muss beide Nachrichtentypen behandeln, nicht nur
`job_status`). Ankommend im API-Prozess: `face_pipeline.signal(asset_id)` wie heute aufrufen — die
Klasse selbst (`FacePipeline`) braucht **keine** Code-Änderung, nur der Aufrufer ändert sich von
„Cross-Thread-Funktionsaufruf" auf „Cross-Process-Nachricht, die denselben Aufruf auslöst".

Konkret zu ändern:
- `caption_job.py::_run_caption_with_preset` (`finally`-Block) und die äquivalente Stelle in
  `tagging_job.py`: statt `face_pipeline.signal(asset_id)` → in den Worker-Prozess-Kontext eine
  Funktion einführen (z.B. `worker/signals.py::emit_pipeline_signal(pipeline, asset_id)`), die die
  `PipelineSignalMessage` auf die Status-Queue schreibt. Diese Funktion braucht Zugriff auf die
  Status-Queue-Instanz — am saubersten über ein Modul-globales, beim Worker-Start gesetztes Handle
  (Analogie zu `face_pipeline.set_loop()` heute), nicht über Parameterdurchreichung durch alle
  Job-Funktionen.
- API-seitiger Status-Forwarder (Phase 1, `jobs/queue.py`): `isinstance`/`type`-Check auf die
  eingehende Nachricht, `pipeline_signal` → `face_pipeline.signal(msg.asset_id)` bzw.
  `classification_pipeline.signal(msg.asset_id)`, `job_status` → wie bisher.

## Aufgabe 4 — Modell-Cache-Umzug

`session_manager` (ONNX-Pool für Florence-2 + WD14) läuft ab dieser Phase ausschließlich im
Worker-Prozess. Prüfen: `main.py`s `_idle_eviction_loop` ruft `session_manager.evict_idle()` —
das muss **nicht** sofort aus `main.py` entfernt werden (volle Migration der Eviction-Loop ist
Phase 3/4, wenn auch die restlichen Engines umziehen), aber ab dieser Phase läuft
`session_manager` faktisch in zwei Adressräumen gleichzeitig, falls `main.py` weiterhin eine
eigene Instanz im API-Prozess hält, die nie benutzt wird. Für diese Phase reicht: verifizieren,
dass die API-Prozess-Instanz von `session_manager` schlicht leer bleibt (keine Sessions geladen,
da keine Aufrufer mehr) — kein funktionales Problem, nur eine tote Instanz bis Phase 4 aufräumt.

## AK dieser Phase

- [ ] Captioning und Tagging laufen sichtbar im Worker-Prozess (Log-Zeile mit Worker-PID oder
      äquivalenter Marker beim Modell-Laden).
- [ ] Ein echtes Bild durch den vollen Import-Pfad schicken (Tagging + Captioning aktiv) — FACE
      wird genau einmal ausgelöst, unabhängig davon, welcher der beiden Jobs zuerst fertig wird
      (beide Reihenfolgen einmal manuell erzwingen/beobachten).
- [ ] Während Captioning/Tagging für mehrere Bilder läuft: Lightbox eines anderen, bereits
      importierten Bildes öffnen — lädt ohne merkbare Verzögerung (der ursprüngliche Symptom-Test).
- [ ] `session_manager`-Instanz im API-Prozess bleibt nachweislich ungenutzt (kein Session-Load-Log
      dort mehr).

## Doc-Updates

- [x] `docs/code-map.md` — Zeilen „Tags" und „Captions & Presets" um den Hinweis „läuft im
      Worker-Prozess" ergänzt.

## Report-Back

**Code fertig, ruff + mypy --strict grün (nur die 3 vorbestehenden `caption_job.py`-Fehler aus
`_run_captioner`, unverändert). Alle vier AK sind Laufzeit-Checks (Worker-PID im Log,
FACE-Reihenfolge, Lightbox-Reaktionsfähigkeit, leere `session_manager`-Instanz) — private-Profil,
nicht von mir gelaufen, siehe „Offene Smoke-Tests" in STATE.md.**

- **Payload-Umfang Tagging:** bestätigt schlank — nur `{"asset_id": asset_id}`, keine weiteren
  Skalare oder Objekte (Gegencheck aus Aufgabe 2 abgeschlossen).
- **Payload-Umfang Captioning:** erweitert um `override_preset_id`/`force` (genau wie im
  README-Kontrakt vorgezeichnet) — `run_caption_job()` reicht beide jetzt durch, `_run_caption()`
  (der alte Wrapper ohne diese Parameter) ist entfallen, da er nach der Erweiterung redundant war.
- **FACE-Auslöse-Test in beiden Reihenfolgen:** nicht live gelaufen. Der Cross-Process-Pfad ist
  aber durchgängig verdrahtet: `caption_job.py`/`tagging_job.py` rufen in ihrem `finally`-Block
  jetzt `worker/signals.py::emit_pipeline_signal()` statt direkt `face_pipeline.signal()` — die
  neue Funktion erkennt selbst, ob sie im Worker- oder API-Prozess läuft (Handle, das
  `worker/process.py` beim Start setzt) und wählt entsprechend IPC oder lokalen Aufruf.
  `jobs/queue.py::_remote_status_forwarder()` empfängt `pipeline_signal`-Nachrichten jetzt und
  ruft `face_pipeline.signal()`/`classification_pipeline.signal()` im API-Prozess auf.

### Abweichung vom Plan-Wortlaut — Architektur-Lücke gefunden und mitgefixt

Beim Umsetzen von Aufgabe 1 fiel auf: `rerun_job.py::run_rerun_job()` ruft `_run_tagging()` und
`_run_caption_with_preset()` **nicht** über `enqueue_tagging()`/`enqueue_caption()` auf, sondern
direkt (`asyncio.to_thread(_run_tagging, asset_id)` etc., synchron im API-Prozess). Ohne Fix hätte
„Bilder erneut verarbeiten" (Rerun) Florence-2/WD14 weiterhin im API-Prozess geladen — genau das,
was AK 4 dieser Phase ausschließt, und der ganze Grund für den Plan (API friert während Inferenz
ein) wäre für den Rerun-Pfad unverändert geblieben.

Fix: neue Methode `JobQueue.enqueue_remote_and_wait()` (reiht im Worker ein, wartet aber auf
DONE/ERROR statt Fire-and-Forget) + `rerun_job.py::_run_remote_step()` als schlanker Wrapper
darüber (fail-fast wie vorher: ein Fehler bricht den Rerun ab). `rerun_job.py`s Tags-/
Caption-Schritte laufen jetzt darüber; Embedding/Heuristics/Categories/Faces bleiben unverändert
lokal (die migrieren erst in Phase 3 — siehe FINDINGS.md, dort wartet derselbe Fix auf dieselbe
Weise für die restlichen vier Schritte).

Nicht im Plan-Wortlaut vorgesehen, aber notwendig, um AK 4 ehrlich zu erfüllen statt sie
stillschweigend zu unterlaufen.
