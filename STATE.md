# STATE

**Aktiver Plan:** (kein aktiver Plan) — P16 complete, Archivierung ausstehend.
**Nächster Schritt:** Plan archivieren (`git mv docs/planning/2026-06-29_p16-generativ-via-comfyui/ docs/archive/2026-06/`), dann nächsten Backlog-Plan wählen.

**Stand:** P16 alle 6 Phasen complete. lint+build grün nach Phase 5.

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
