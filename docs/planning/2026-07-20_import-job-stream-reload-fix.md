# Bugfix: Galerie lädt nach Import nicht (toter Job-Stream)

## Overview

| Phase | Thema | Modul | Rating | Status |
|---|---|---|---|---|
| 1 | SSE-Reconnect für den Job-Stream | Frontend | standard | complete |

## Ausgangsbefund (Kontext, nicht nochmal recherchieren)

**Toter Job-Stream ohne Reconnect:** `frontend/src/app/services/jobs.service.ts::streamJobs()`
schließt bei JEDEM `EventSource.onerror` hart (`source.close()` + `observer.error()`) — auch bei
einem kurzen, an sich selbstheilenden Verbindungsabbruch. `jobs.effects.ts::loadStream$` hat keinen
Retry; `loadStream()` wird laut `shell.ts` genau einmal beim App-Start dispatcht. Reißt die
Verbindung einmal ab, bleibt sie für den Rest der Session tot.
`gallery.effects.ts::reloadAfterImport$` hängt komplett an diesem Stream (`jobsActions.upsertJob`
mit `kind: import|scan`, `state: done`) — kein anderer Pfad triggert einen Galerie-Reload nach
Import (`onImported()` in `shell.ts` öffnet nur den Job-Dock).

**Kaltstart-Ruckler ist kein Bug, sondern gewollt:** Der erste Import nach App-Start (oder nach
>120s Idle) triggert einen echten Kaltstart der ONNX-Modelle (`buffalo_l.py` u.a.) — das ist eine
bewusste Architektur-Entscheidung ([ADR-002](../decisions/002-generatives-backend.md), „VRAM-
Koordination: ONNX-Sessions werden bei Bedarf evicted"), damit VRAM für parallel laufendes ComfyUI
frei bleibt. **Kein Warmup, kein Vorladen — Modelle bleiben strikt lazy-load + idle-evict.** Der
Ruckler selbst ist akzeptiert; das Problem war nur, dass sich die Galerie davon nie wieder erholt
hat, weil der SSE-Stream dabei wahrscheinlich abreißt und tot bleibt. Genau das behebt Phase 1.

## Finale Akzeptanzkriterien (fürs Ganze)

- Ein einmaliger SSE-Verbindungsabbruch (z.B. durch den Kaltstart-Ruckler beim ersten Import)
  beendet den Job-Stream nicht dauerhaft — die App verbindet sich innerhalb weniger Sekunden selbst
  neu, ohne Reload der Seite.
- Modell-Ladeverhalten bleibt unangetastet: strikt lazy-load beim ersten Bedarf, idle-evict nach
  Timeout — keine Änderung an `session_manager.py` oder `main.py::_lifespan`.

## Smoke-Checkliste (macht der User nach Umsetzung)

1. 🔴 **Wackelstelle:** SSE-Reconnect durch den Angular-Dev-Proxy (`proxy.conf.json`) — manche Proxies
   buffern/timeouten Server-Sent Events. Check: App offen lassen, Backend-Fenster kurz neu starten
   (Strg+C + `uv run uvicorn ...` erneut, oder `start.cmd` einmal durchlaufen lassen), DevTools →
   Network → `/api/jobs/stream` beobachten — muss sich innerhalb weniger Sekunden neu verbinden
   (neuer Request erscheint), nicht auf „failed" stehen bleiben.
2. Frischer App-Start, dann sofort ersten Import anstoßen (bewusster Kaltstart-Fall). Galerie zeigt
   die importierten Bilder danach ohne manuelles Neuladen der Seite — auch wenn der Import selbst
   ein paar Sekunden zäh war.
3. Zweiter Import kurz danach (Modelle jetzt warm) — Galerie aktualisiert sich weiterhin.

## Phase 1 — SSE-Reconnect für den Job-Stream

**Kontext (lesen vor Umsetzung):**
- `frontend/src/app/services/jobs.service.ts` — `streamJobs()`, aktuell schließt jeder `onerror`
  die Verbindung hart.
- `frontend/src/app/store/jobs/jobs.effects.ts` — `loadStream$`, konsumiert `streamJobs()`.
- `frontend/src/app/shell/shell.ts` — dispatcht `jobsActions.loadStream()` einmalig (Zeile ~68).

**Änderungen:**

1. `jobs.service.ts::streamJobs()` — `onerror`-Handler ersetzen: nur terminal fehlschlagen, wenn
   `source.readyState === EventSource.CLOSED` (native Browser-Reconnect-Logik hat selbst aufgegeben).
   Bei `CONNECTING` (native Retry läuft) **nichts tun** — kein `close()`, kein `observer.error()`,
   nur ein `console.warn('[jobs] SSE reconnecting…')` fürs Debugging. Beispiel-Logik:
   ```ts
   source.onerror = (): void => {
     if (source.readyState === EventSource.CLOSED) {
       observer.error(new Error('SSE connection failed'));
     } else {
       console.warn('[jobs] SSE reconnecting…');
     }
   };
   ```
2. `jobs.effects.ts::loadStream$` — den `jobsService.streamJobs()`-Call mit RxJS `retry({ delay: 3000 })`
   umschließen (innerhalb des `switchMap`, vor `catchError`), damit ein echter Terminal-Error (Fall
   `CLOSED` oben) automatisch eine neue `EventSource` aufbaut, statt den Stream endgültig sterben zu
   lassen. `catchError` bleibt als letztes Netz (z.B. wenn `/api/jobs/stream` dauerhaft 404/500 liefert)
   und dispatcht weiterhin `streamError`.
3. Kein Änderungsbedarf an `gallery.effects.ts` oder `shell.ts` — `reloadAfterImport$` funktioniert
   bereits korrekt, sobald der Stream nicht mehr dauerhaft tot geht.

**AK der Phase:**
- Ein `onerror`-Event mit `readyState !== CLOSED` beendet das Observable nicht.
- Ein echter Terminal-Error löst nach 3s automatisch eine neue Verbindung aus (sichtbar im Log als
  neuer `console.warn`/Reconnect, ohne dass die Seite neu geladen werden muss).
- `npm run lint` + `npm run build` grün.

**Doc-Updates:** keine (kein neues Feature, kein Code-Map-Eintrag nötig).

## Deviations from plan

Ursprünglich zweite Phase geplant (Modell-Warmup beim Backend-Start, um den Kaltstart-Ruckler selbst
zu vermeiden). Vom User abgelehnt: Modelle bleiben bewusst strikt lazy-load + idle-evict
([ADR-002](../decisions/002-generatives-backend.md)), damit VRAM für parallel laufendes ComfyUI frei
bleibt — ein Warmup beim Start würde dauerhaft VRAM belegen, nur weil die App läuft. Phase 2 ersatzlos
gestrichen; der Ruckler selbst ist kein Bug, nur der tote Reconnect danach.

## Summary

`onerror` beendet die SSE-Verbindung zum Job-Stream nur noch, wenn der Browser selbst aufgegeben hat
(`readyState === CLOSED`); ein transienter Aussetzer lässt den nativen Reconnect ungestört laufen.
Zusätzlich holt `retry({ delay: 3000 })` im Effekt einen echten Terminal-Error nach 3s zurück. Kein
Eingriff ins Modell-Ladeverhalten (bleibt lazy-load + idle-evict, ADR-002).

## Files touched

- `frontend/src/app/services/jobs.service.ts` — `onerror`-Handler auf `readyState`-Check umgestellt.
- `frontend/src/app/store/jobs/jobs.effects.ts` — `retry({ delay: 3000 })` vor `catchError` ergänzt.

## Commits

- `docs(planning): add plan for import job-stream reload fix`
- (Implementierungs-Commit folgt)

## Follow-ups

Keine.
