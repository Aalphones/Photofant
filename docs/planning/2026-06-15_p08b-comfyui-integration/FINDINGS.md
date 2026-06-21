# P8b — FINDINGS

> Notizen, Spike-Ergebnisse und Entscheidungen während der Umsetzung. Beim Archivieren ins README (Summary/Deviations) destillieren.

## Phase-3-Entscheidungen (2026-06-21)

- **Antwort-Schema `/run` gibt nur `job_id` zurück**, nicht `prompt_id`. Die `prompt_id` ist erst nach der async Upload+Prompt-Sequenz bekannt (Worker, nicht Route-Handler). Kontrakt leicht abgewichen: `{jobs: [{job_id}]}`.
- **Status-Polling (`/history/{id}`)** als Client-Methode implementiert, aber noch nicht im Worker-Aufruf verdrahtet — Phase 4 baut die Run-Leiste und kann SSE dort einbinden.
- **Job-Fehler-Isolation** ist durch die bestehende Queue-Mechanik abgedeckt (per-Job try/except im `_worker`); kein eigener Mechanismus nötig.

- [x] → Phase 4: `get_history`-Polling im Worker aktivieren, sobald Run-Leiste SSE-Events konsumiert. — Eingearbeitet: Phase 5 muss `prompt_id`-Lookup über eigenen Flow lösen (run gibt nur job_id zurück).

- [ ] → Phase 5: `runWorkflow` gibt nur `job_id` zurück (kein `prompt_id`). Import-Flow in Phase 5 muss History via Job-Queue-State oder separatem `/api/comfyui/results?job_id=`-Endpoint holen. Alternativ: output_dir-Scan als primärer Pfad (Konzept §8.2 erlaubt das).

## Offene Punkte / Risiken

- **API-Format ≠ UI-Format.** Nur das API-Format-JSON ist patch- und queuebar (Konzept §6). Introspektion + Validierung müssen das prüfen, sonst stilles Scheitern.
- **ComfyUI ohne Auth, Port 8188 Default.** Lokal unkritisch; bei Remote-Instanz Reverse-Proxy (Konzept §1/§6). Offline-Garantie: nur konfigurierte Instanz ansprechen.
- **`kind = mask` hängt an P9 Phase 4** (Masken-Editor). In Phase 4 nur gegated, nicht implementiert. Falls Masken-Workflows früher gebraucht: minimalen Masken-Editor vorziehen.
- **Output-Cleanup liegt bei ComfyUI** — Photofant verwaltet die `output/`-Dateien nicht (Konzept §6).
- **Koexistenz mit P9:** ADR-003 muss das Verhältnis zu ADR-002 sauber abgrenzen (wann Trigger, wann in-process). Doppelte Capability-Anzeige in der UI vermeiden.

## Spikes

## Entscheidungen
