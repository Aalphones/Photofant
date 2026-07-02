# Phase 4 — Frontend: Worker-Slider in Verarbeitung

**Rating:** standard (etablierten Slider-Pattern der Verarbeitung-Sektion 1:1 wiederverwenden)

## Kontext (vor dem Start lesen)

- `frontend/src/app/features/einstellungen/verarbeitung/verarbeitung.html` Zeile ~206-221 —
  Referenz-Pattern für einen Threshold-Slider (`face_auto_threshold`): natives
  `<input type="range">` mit Klasse `verarbeitung__slider`, plus `verarbeitung__zeile-sub` für
  Subtext.
- `frontend/src/app/features/einstellungen/verarbeitung/verarbeitung.ts` Zeile 27 (Muster
  `linkedSignal`), Zeile 50-53 (Label-Computed), Zeile 151-155 (`onFaceAutoThresholdChange` —
  Clamping + Commit-Pattern).
- `frontend/src/app/models/config.model.ts` Zeile 23-41 (`ProcessingConfig`-Interface),
  Zeile 43-60 (`PROCESSING_CONFIG_DEFAULTS`).
- `frontend/src/app/store/models/models.effects.ts` Zeile 14-32 (`PROCESSING_CONFIG_KEY_MAP`),
  Zeile 34-54 (`extractProcessingConfig`).
- `frontend/src/app/store/models/models.selectors.ts` — `modelsSelectors.selectVram` ist bereits
  im selben Store vorhanden (aktuell von `features/modelle/modelle.ts` genutzt); Verarbeitung
  kann denselben Selector + `modelsActions.loadVram()` wiederverwenden, kein neuer State nötig.
- Design: **kein dediziertes Mockup** für diese zwei Slider — die Verarbeitung-Sektion ist ein
  bestehender, etablierter Screen; diese Phase erweitert ihn um zwei Zeilen im exakt gleichen
  visuellen Pattern wie die vorhandenen Threshold-Slider (keine neue Struktur, kein Erfinden).

## Idiotensicherheits-Check

- Beschriftung klar in Alltagssprache: „Tagging-Worker" / „Caption-Worker" mit Subtext, was das
  bewirkt (nicht nur die Zahl) — z.B. „Wie viele Bilder gleichzeitig getaggt werden. Mehr =
  schneller, braucht aber mehr Grafikspeicher."
- „Empfohlen: N" direkt neben dem Slider sichtbar (kein Wissen über die eigene GPU-VRAM-Menge
  vorausgesetzt).
- Kein Freitext-Zahlenfeld — nur der Slider mit Range 1-4, macht ungültige Werte unmöglich.

## Akzeptanzkriterien (falsifizierbar)

1. In der Verarbeitung-Sektion erscheinen zwei neue Zeilen (gleiche Struktur wie die
   bestehenden Threshold-Zeilen: Label, Slider `min=1 max=4 step=1`, aktueller Wert,
   `zeile-sub`-Subtext mit Erklärung + „Empfohlen: N"):
   - „Tagging-Worker" (bindet an `taggingWorkers`)
   - „Caption-Worker" (bindet an `captioningWorkers`)
2. Der „Empfohlen: N"-Teil zeigt den Wert aus `selectVram().suggested_tagging_workers` bzw.
   `.suggested_captioning_workers`; zeigt nichts (oder „unbekannt"), wenn `null` (keine GPU
   erkannt) — kein Rateflasch-Wert.
3. Verschieben des Sliders committet (analog `onFaceAutoThresholdChange`) per PATCH an
   `/api/config` mit `tagging_workers`/`captioning_workers`.
4. Seite neu laden → der zuletzt gesetzte Wert bleibt (kommt aus `extractProcessingConfig`).

## Checkliste

- [x] `ProcessingConfig`: `taggingWorkers`, `captioningWorkers` ergänzt (+ Defaults `1`)
- [x] `PROCESSING_CONFIG_KEY_MAP`: beide neuen Keys → `tagging_workers`/`captioning_workers`
- [x] `extractProcessingConfig`: beide Keys mit Fallback auf Default
- [x] `verarbeitung.ts`: `linkedSignal` + Input/Change-Handler für beide Slider (Clamp 1-4,
      ganzzahlig), Vram-Selector eingebunden, `loadVram()` dispatchen falls noch nicht geladen
- [x] `verarbeitung.html`: zwei neue Zeilen im bestehenden Slider-Pattern, inkl. „Empfohlen: N"
- [x] `docs/code-map.md`: geprüft — keine neue Zeile nötig, `features/einstellungen/verarbeitung`
      und `settings.py`/`vram.py` stehen bereits unter „Einstellungen" bzw. „Modell-Management"

## Report-Back

Beide Slider sitzen in der Auto-Pipeline-Gruppe der Verarbeitung-Sektion, direkt nach dem
CLIP-Embedding-Schalter — gleiches Slider-Pattern wie die bestehenden Threshold-Regler
(`verarbeitung__slider-gruppe`), Range 1-4, „Empfohlen: N" im Subtext, ausgeblendet wenn die
GPU-Empfehlung `null` ist. `tsc --noEmit` läuft fehlerfrei durch; kein `ng test` (private-Profil).
Offen: manueller UI-Smoke — Slider ziehen, App neu laden, Wert bleibt (AK 1-4) — läuft mit der
finalen Smoke-Checkliste am Plan-Ende, da dort ohnehin ein Live-Backend gebraucht wird.
