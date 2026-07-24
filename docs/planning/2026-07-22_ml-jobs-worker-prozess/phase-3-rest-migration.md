# Phase 3 — Rest-Migration: Embedding, Heuristics, Classification, Face, Clustering, Dupe-Scan

**Komplexität:** standard (Muster aus Phase 2 wiederholen, kein neuer Mechanismus mehr nötig).

## Kontext (lesen vor dem Start)

- Phase 2 Report-Back — das Payload-Umbau-Muster und der `pipeline_signal`-Mechanismus sind dort
  bewiesen. Diese Phase wendet beides auf die restlichen sechs Job-Kinds an, erfindet nichts neu.
- [backend/photofant/jobs/classification_pipeline.py](../../../backend/photofant/jobs/classification_pipeline.py) —
  identisches Muster zu `face_pipeline.py`, Abhängigkeit: TAGGING (schon in Phase 2 migriert) +
  EMBEDDING (migriert in dieser Phase). Bleibt wie `face_pipeline` im API-Prozess.
- `backend/photofant/jobs/queue.py` — `_BACKGROUND_PRIORITY`/`_BACKGROUND_KINDS`
  (Heuristics/Embedding/Classification/Face/Clustering/Dupe-Scan). Diese Kinds wandern komplett
  in `_REMOTE_KINDS`; die lokale Background-Queue im API-Prozess wird dadurch ungenutzt (Cleanup
  in Phase 4, hier nicht vorziehen — erst verifizieren, dass wirklich nichts mehr lokal läuft).
- `backend/photofant/jobs/clustering_job.py`, `dupe_scan_job.py` — kein Pipeline-Tracker-Vorbild
  (keine `*_pipeline.py`-Datei) — vor dem Migrieren verifizieren, wie/wann sie ausgelöst werden
  (UI-Aktion? Wartungsseite? Teil der Import-Pipeline?), damit der Payload-Umbau die richtigen
  Auslöser-Stellen trifft.

## Aufgabe 1 — Payload-Umbau: Embedding, Heuristics, Classification, Face, Clustering, Dupe-Scan

Für jeden der sechs Job-Kinds, einzeln:
1. `enqueue_*`-Funktion auf den Remote-Pfad umstellen (Payload-Dict statt `coro_factory`).
2. Dispatch-Tabelle (`worker/dispatch.py`) um die Zeile ergänzen.
3. `JobKind` in `_REMOTE_KINDS` aufnehmen.
4. Verifizieren, dass der Payload nur JSON-simple Werte enthält (Risiko README — bei jedem Job
   einzeln prüfen, nicht pauschal von `caption_job.py` annehmen).

Face und Classification zusätzlich: der `enqueue_face`/`enqueue_classification`-Aufruf, den
`face_pipeline._schedule_face`/`classification_pipeline._schedule` heute per
`run_coroutine_threadsafe` auf die lokale Coroutine im API-Prozess absetzen, geht jetzt über den
ganz normalen Remote-Enqueue-Pfad (der Aufruf bleibt im API-Prozess, nur sein Ziel ist jetzt der
Worker statt eine lokale Queue) — keine Strukturänderung an `face_pipeline`/`classification_pipeline`
nötig, nur die Zielfunktion (`enqueue_face`/`enqueue_classification`) ändert sich intern wie jeder
andere migrierte Job.

## Aufgabe 2 — Cross-Process-Signal für CLASSIFICATION

Gleicher Mechanismus wie Phase 2 Aufgabe 3, gespiegelt auf `classification_pipeline`: Tagging
(schon migriert) und Embedding (diese Phase) senden nach Fertigstellung eine
`PipelineSignalMessage(pipeline="classification", asset_id=...)` statt direkt
`classification_pipeline.signal()` zu rufen. Der API-seitige Forwarder aus Phase 1/2 behandelt
`pipeline="classification"` bereits als Fall (dort schon als Zweig vorgesehen) — hier nur die
Absender-Seite (Embedding-Job) ergänzen, Tagging sendet das Signal seit Phase 2 schon (dort ging
es nur an `face_pipeline`, jetzt kommt `classification_pipeline` als zweiter Empfänger desselben
Tagging-Abschlusses dazu — Tagging signalisiert nach Fertigstellung an **beide** Pipelines).

## Aufgabe 3 — Clustering + Dupe-Scan ohne Pipeline-Tracker

Diese beiden haben keine Prerequisite-Zähler-Logik — sie werden vermutlich direkt aus einer
API-Route oder einem Wartungs-Job ausgelöst. Payload-Umbau wie gewohnt, aber **ohne** zusätzlichen
Signal-Mechanismus — einfacher Fall, nur zur Vollständigkeit hier aufgeführt, damit keine der acht
Job-Arten übersehen wird.

## Aufgabe 4 — Idle-Eviction-Loop umziehen

**🟡 Vorgezogener Teilfix (2026-07-24, außerhalb der Plan-Reihenfolge):** Nutzer meldete
VRAM-Leck live nach Phase 2 (Tagging/Captioning-Modelle blieben nach Import dauerhaft geladen).
Ursache war exakt diese Aufgabe. Um die Lücke nicht bis Phase 3 offen zu lassen, läuft
`worker/process.py::_idle_eviction_loop` (analog zu `main.py`s Version) bereits **seit jetzt** im
Worker-Prozess, gestartet/gecancelt in `_run_worker` (`eviction_task`, symmetrisch zu
`forwarder_task`), plus expliziter `generative_engine.unload()`/`gguf_engine.unload()`/
`session_manager.shutdown()` im `finally`-Block beim Worker-Stop. Das deckt die zwei migrierten
Job-Arten (CAPTIONING/TAGGING) ab. `main.py::_idle_eviction_loop` bleibt **bewusst unverändert**
stehen, weil CLIP/SigLIP2/DINOv2/buffalo_l (Embedding/Face) bis Phase 3 weiterhin im API-Prozess
laufen und die dortige Schleife brauchen.

Wenn diese Phase jetzt umgesetzt wird: die Worker-seitige Schleife existiert schon (nicht
neu bauen) — offen bleibt nur noch der **zweite Teil**, der ursprünglich hier beschrieben war:
`main.py::_idle_eviction_loop` (`session_manager.evict_idle()`, `generative_engine.evict_idle()`,
`gguf_engine.evict_idle()`) läuft nach vollständiger Migration von Embedding/Heuristics/
Classification/Face/Clustering/Dupe-Scan komplett gegen tote, ungenutzte Instanzen im API-Prozess.
`main.py` verliert dann den `eviction_task`-Code; `session_manager`/`generative_engine`/
`gguf_engine`-Importe in `main.py` fallen ebenfalls weg, sofern nichts anderes dort noch darauf
zugreift (verifizieren: `grep -n "session_manager\|generative_engine\|gguf_engine"
backend/photofant/main.py` sollte danach nur noch im Worker-Kontext auftauchen, nicht mehr in
`main.py`).

## AK dieser Phase

- [ ] Alle acht Job-Kinds (Tagging, Captioning, Embedding, Heuristics, Classification, Face,
      Clustering, Dupe-Scan) laufen nachweislich im Worker-Prozess.
- [ ] Ein echtes Bild durch den vollen Import-Pfad — CLASSIFICATION wird genau einmal ausgelöst,
      unabhängig von der Fertigstellungs-Reihenfolge Tagging/Embedding.
- [ ] `main.py` importiert nach dieser Phase keine Inferenz-Engines mehr direkt.
- [ ] Import eines größeren Batches (z.B. 20+ Bilder) während dauerhaft in der Lightbox geblättert
      wird — durchgehend responsiv, kein Hänger zu irgendeinem Zeitpunkt der Verarbeitung.

## Doc-Updates

- [ ] `docs/code-map.md` — Zeilen „Klassifizierung & Heuristik", „Empfehlungen" (falls
      Embedding dort referenziert wird), „Personen, Faces, Review", „Inferenz-Infra" um den
      Worker-Prozess-Hinweis ergänzen.

## Report-Back

_(nach Umsetzung ausfüllen: Ergebnis des CLASSIFICATION-Auslöse-Tests, tatsächliche Auslöser-
Stellen von Clustering/Dupe-Scan falls abweichend von der Vermutung oben, jede Abweichung vom
Plan-Wortlaut)_
