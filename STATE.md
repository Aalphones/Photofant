# STATE

**Aktiver Plan:** P16 — Generativ via ComfyUI (Abriss P9), `docs/planning/2026-06-29_p16-generativ-via-comfyui/` · Phase 3/6 (pending)
**Nächster Schritt:** Phase 3 — P9 in-process Backend abreißen (`api/generative.py`, upscale/flux_edit/inpaint/install_generative-Jobs, Manifest-Rollen). Sweep: nur Bild-Generativ-Rollen raus, `heavy_captioner` bleibt.

**Hinweis:** Phase 4 complete (2026-06-29). Reihenfolge: Phase 3 vor 5, weil Phase 5 auf dem bereinigten Backend aufbaut.

---

## Backlog & Abgeschlossenes

**Abgeschlossen:**
- P9 Phase 1–5: Generative Features vollständig — archiviert in `docs/archive/2026-06/2026-06-12_p09-generativ/` (2026-06-23)
- P12: Konfigurierbare Gesichtserkennung-Parameter — complete (2026-06-22)
- P14 Job-Queue Zwei-Spuren + Prio — archiviert in `docs/archive/2026-06/2026-06-27_p14-job-queue-prio-parallelisierung.md` (2026-06-27)
- Falsche Personen-Zuordnungen (Wartungs-UI + Reconcile) — archiviert in `docs/archive/2026-06/2026-06-28_falsche-personen-zuordnungen.md` (2026-06-28)

**Backlog-Pläne (größere Features):**
- P10 Trainingssets: `docs/planning/2026-06-12_p10-trainingssets-export/`
- P11 Duale Duplikaterkennung (pHash=exact-only + CLIP): `docs/planning/2026-06-22_p11-duale-duplikaterkennung/`
- P13 Person-Bulk-Import: `docs/planning/2026-06-22_p13-person-bulk-import/`
- P15 Lightbox-Angleichung ans Mockup (6 Phasen): `docs/planning/2026-06-28_p15-lightbox-angleichung/`

**Hinweis:** P16 (aktiv) reißt das oben als abgeschlossen gelistete **P9** (in-process generatives Backend) ab — Upscale/Edit/Inpaint laufen danach nur noch über ComfyUI. ADR-008 ersetzt ADR-002.
