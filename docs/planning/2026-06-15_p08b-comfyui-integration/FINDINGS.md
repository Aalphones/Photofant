# P8b — FINDINGS

> Notizen, Spike-Ergebnisse und Entscheidungen während der Umsetzung. Beim Archivieren ins README (Summary/Deviations) destillieren.

## Offene Punkte / Risiken

- **API-Format ≠ UI-Format.** Nur das API-Format-JSON ist patch- und queuebar (Konzept §6). Introspektion + Validierung müssen das prüfen, sonst stilles Scheitern.
- **ComfyUI ohne Auth, Port 8188 Default.** Lokal unkritisch; bei Remote-Instanz Reverse-Proxy (Konzept §1/§6). Offline-Garantie: nur konfigurierte Instanz ansprechen.
- **`kind = mask` hängt an P9 Phase 4** (Masken-Editor). In Phase 4 nur gegated, nicht implementiert. Falls Masken-Workflows früher gebraucht: minimalen Masken-Editor vorziehen.
- **Output-Cleanup liegt bei ComfyUI** — Photofant verwaltet die `output/`-Dateien nicht (Konzept §6).
- **Koexistenz mit P9:** ADR-003 muss das Verhältnis zu ADR-002 sauber abgrenzen (wann Trigger, wann in-process). Doppelte Capability-Anzeige in der UI vermeiden.

## Spikes

## Entscheidungen
