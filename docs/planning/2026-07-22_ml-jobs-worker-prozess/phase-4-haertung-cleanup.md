# Phase 4 — Härtung + Cleanup

**Komplexität:** standard (kein neuer Mechanismus, macht das Bestehende ausfallsicher und aufgeräumt).

## Kontext (lesen vor dem Start)

- Phase 1 Aufgabe 5 (`main.py`-Lifecycle) — Crash-Erkennung war dort bewusst nur Grundgerüst
  („stirbt der Worker, wird das laut geloggt"). Diese Phase baut den Respawn drauf.
- `backend/photofant/jobs/queue.py` — `_tagging_queue`/`_captioning_queue`/`_background_queue`
  und die zugehörigen `_tagging_worker`/`_captioning_worker`/`_background_worker`-Coroutinen sind
  nach Phase 3 im API-Prozess ungenutzt (alle Kinds, die sie bedienen, sind jetzt in
  `_REMOTE_KINDS`). Diese Phase entfernt den toten Code — **nicht früher**, sonst fehlt die
  Rückfalloption, falls eine Migrationsphase doch einen Job übersehen hat.
- README „Bewusst draußen" — Circuit-Breaker/Backoff über eine einfache Neustart-Zählung hinaus
  ist explizit nicht Teil dieser Phase.

## Aufgabe 1 — Crash-Erkennung + Auto-Respawn

`JobQueue` (API-seitige Instanz) bekommt eine Health-Check-Coroutine, die periodisch
`worker_process.is_alive()` prüft (der `mp.Process`-Handle aus `main.py` muss dafür erreichbar
sein — z.B. als Attribut auf `job_queue` selbst, gesetzt beim Start). Stirbt der Prozess:

1. Alle `JobStatus`-Einträge mit `state == RUNNING`, deren `kind` in `_REMOTE_KINDS` liegt, auf
   `state = ERROR`, `error = "Worker-Prozess abgestürzt"` setzen und benachrichtigen (Frontend
   zeigt den Job korrekt als fehlgeschlagen statt für immer als „läuft").
2. Einen neuen Worker-Prozess starten (gleiche `mp.Process(target=run_worker_process, ...)`-Zeile
   wie beim initialen Start — als eigene Funktion `_spawn_worker()` faktorisieren, damit Erststart
   und Respawn denselben Code nutzen).
3. Eine einfache Zählung (z.B. „max. 5 Neustarts pro 10 Minuten, danach aufgeben und laut loggen")
   gegen Crash-Loops — kein volles Circuit-Breaker-Pattern, siehe „Bewusst draußen".

## Aufgabe 2 — Dead-Code-Entfernung in `queue.py`

Verifizieren (`grep -n "_tagging_queue\|_captioning_queue\|_background_queue" backend/photofant/jobs/queue.py`
und alle Aufrufer), dass keine der drei lokalen Queues nach Phase 3 noch befüllt wird — dann
`_tagging_queue`, `_captioning_queue`, `_background_queue`, `_tagging_worker_tasks`,
`_captioning_worker_tasks`, `_background_worker_task`, `resize_tagging_workers()`,
`resize_captioning_workers()`, `_scale_pool()` (falls nach Entfernung ungenutzt) sowie die
Settings `tagging_workers`/`captioning_workers` in `settings.py` entfernen oder — falls die
Pool-Größe im Worker-Prozess weiterhin konfigurierbar bleiben soll — auf ein neues,
Worker-seitiges Äquivalent ummünzen, statt sie tot im API-Prozess liegen zu lassen.

⚠️ Bewusst nicht vorher entfernen: diese Aufgabe ist der letzte Schritt, nachdem Phase 2 und 3
bewiesen haben, dass wirklich nichts mehr lokal läuft. Vorzeitiges Entfernen würde eine
Rückfalloption kappen, falls eine Migration doch unvollständig war.

## Aufgabe 3 — Settings für den Worker-Prozess

Falls Aufgabe 2 ergibt, dass `tagging_workers`/`captioning_workers` weiterhin sinnvoll
konfigurierbar sein sollen (Pool-Größe pro Modelltyp **innerhalb** des einen Worker-Prozesses,
unverändert zum heutigen Verhalten — nur der Prozess drumherum ist neu): Settings-Keys bleiben
wie sie sind, der Worker-Prozess liest sie beim Start genauso wie heute die API es tat
(`load_settings()` funktioniert identisch in jedem Prozess, da rein dateibasiert). Kein neuer
Settings-Key nötig, sofern die Bedeutung gleich bleibt — nur nachprüfen, nicht blind neu erfinden.

## Aufgabe 4 — Finaler End-to-End-Beweis

Der eigentliche Zweck des ganzen Plans: das ursprüngliche Symptom gezielt reproduzieren und
widerlegen.

1. Import mit einem größeren Batch (mind. 20-30 Bilder) anstoßen, aktiver Captioner Florence-2-
   Base (das leichte Modell, mit dem das Problem ursprünglich beobachtet wurde).
2. Während der Import läuft (alle acht Job-Kinds potenziell aktiv): wiederholt durch die Galerie
   scrollen, mehrfach Bilder in der Lightbox öffnen/schließen, eine Suche ausführen.
3. Erwartung: keine spürbaren Hänger zu keinem Zeitpunkt — das ist der AK, an dem der ganze Plan
   sich misst, nicht ein isolierter Unit-Test.

## AK dieser Phase

- [ ] Worker-Prozess gezielt hart beendet (Task-Manager) während ein Job läuft: API bleibt
      erreichbar, betroffener Job wird `error`, ein neuer Worker kommt binnen wenigen Sekunden
      automatisch hoch, der nächste eingereihte Job läuft normal durch.
- [ ] Fünf aufeinanderfolgende erzwungene Abstürze innerhalb kurzer Zeit lösen die
      Crash-Loop-Bremse aus (laut geloggt, kein Endlos-Respawn).
- [ ] `queue.py` enthält keinen toten Code mehr für die migrierten Job-Kinds.
- [ ] Finaler End-to-End-Beweis (Aufgabe 4) bestanden — das war der Auslöser für den ganzen Plan.
- [ ] Normaler Shutdown weiterhin ohne Zombie-Prozess (Regressionscheck ggü. Phase 1).

## Doc-Updates

- [ ] `docs/code-map.md` — „Jobs / Queue"-Zeile final auf den Endzustand bringen (nicht mehr
      „Hinweis ergänzt", sondern die tatsächliche Architektur beschreiben: API-Prozess für
      I/O-Jobs, Worker-Prozess für alle Modell-Inferenz-Jobs).
- [ ] `docs/decisions/033-ml-jobs-worker-prozess.md` — falls sich beim Umsetzen relevante Details
      gegenüber Phase 1 geändert haben (z.B. tatsächliche Respawn-Strategie), ADR nachziehen statt
      einen Drift zwischen Entscheidung und Code stehen zu lassen.

## Report-Back

_(nach Umsetzung ausfüllen: Ergebnis des finalen End-to-End-Beweises — das ist der wichtigste
Eintrag im ganzen Plan —, tatsächliches Respawn-Verhalten, was an Dead Code tatsächlich entfernt
wurde)_
