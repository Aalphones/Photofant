# Findings — Worker-Prozess für ML-Inferenz-Jobs

Getaggte Erkenntnisse aus der Umsetzung, die eine spätere Phase betreffen. Format:
`- [ ] → Phase N: <Erkenntnis>`. Wird von `mode-implementing` gepflegt.

- [x] → Phase 2: Konfidenz-Ausweis-Punkt 2 (SQLite aus zwei echten Prozessen) konnte in Phase 1
      nicht geprüft werden — der DEMO-Job rührt die DB nicht an. Sobald CAPTIONING/TAGGING im
      Worker laufen, den Check nachholen: parallel aus API- und Worker-Prozess lesen/schreiben,
      auf `database is locked` prüfen (README „Konfidenz-Ausweis" Punkt 2).
      → Code-seitig fertig (CAPTIONING/TAGGING schreiben jetzt aus dem Worker-Prozess in dieselbe
      SQLite-DB, die der API-Prozess parallel liest/schreibt). Der eigentliche Live-Check ist
      **nicht** gelaufen (private-Profil, kein Selbsttest) — Teil der Phase-2-Smoke-Checkliste
      an den User (STATE.md).

- [ ] → Phase 3: **Architektur-Lücke in `rerun_job.py` gefunden und für Tags/Caption in Phase 2
      mitgefixt — beim Migrieren von EMBEDDING/HEURISTICS/CLASSIFICATION/FACE denselben Fix
      wiederholen.** `run_rerun_job()` ruft die privaten Job-Funktionen (`_run_tagging`,
      `_run_caption_with_preset`, und bisher auch `_run_embedding`/`_run_heuristics`/
      `_run_classification`/`_run_face_job`) **direkt** auf, nicht über
      `enqueue_*()`/`job_queue.enqueue()` — das war schon vor diesem Plan so (Rerun ist ein
      Bulk-Meta-Job, der pro Asset mehrere Schritte sequenziell selbst durchläuft statt sie
      einzureihen, siehe `classification_pipeline.py`-Docstring: „rerun path, which calls
      classification directly"). Für TAGGING/CAPTIONING wurde das in Phase 2 durch einen neuen
      `job_queue.enqueue_remote_and_wait()`-Pfad ersetzt (wartet auf den Worker statt lokal zu
      rechnen) — sonst hätte Rerun weiterhin Florence-2/WD14 im API-Prozess geladen und Phase 2s
      eigene AK „`session_manager`-Instanz im API-Prozess bleibt ungenutzt" verletzt. **Derselbe
      Bug wird in Phase 3 für EMBEDDING/HEURISTICS/CLASSIFICATION/FACE erneut auftauchen**, sobald
      deren `_run_*`-Funktionen aus der API- in die Worker-Ausführung wandern — `rerun_job.py`s
      direkte Aufrufe müssen dann ebenfalls auf `enqueue_remote_and_wait()` umgestellt werden
      (Muster: `_run_remote_step()` in `rerun_job.py`, 1:1 wiederverwendbar).
