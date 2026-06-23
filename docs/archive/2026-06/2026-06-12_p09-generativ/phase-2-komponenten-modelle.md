# P9 · Phase 2 — Komponenten-Modelle & VRAM

> Rating: **heikel** (P4-Validierung wird um die fehleranfälligste Variante erweitert) · Status: **done**

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (components, Warnung statt Gate)
- [Konzept](../../Konzept-Photofant.md) §12.1 (Komponenten-Form), §12.2, **§12.4 (VRAM-Matrix)**, §19.7
- P4 Phase 3 (Validator-Pipeline — wird erweitert, nicht dupliziert)

## Akzeptanzkriterien

- `register-local` mit `components`-Map: je Komponente eigener Picker, eigene Validierung (Format/Rolle/Ladbarkeit), Pfade beliebig verstreut; Vollständigkeits-Gate (alle Pflichtteile) vor Aktivierung.
- Manifest-Erweiterung: Flux-/SeedVR2-Einträge mit Varianten (bf16/fp8/GGUF), Begleitdateien (Qwen3-Encoder, VAEs), erwarteten Familien (für die Warnung), VRAM-Bedarf je Variante.
- VRAM-Erkennung (nvidia-smi/torch) → Varianten-Empfehlung im Download-Dialog (§12.4-Matrix); `MODEL_VRAM_EXCEEDED` als Empfehlung, nie Block.
- Kompatibilitäts-Check (Stufe 6): Familie-Mismatch → Warning-Dialog mit „trotzdem verwenden" (§19.7).
- Modelle-View: Generierung-Tier wird echt (Karten, Komponenten-Status pro Teil, Acquisition-Dialoge nach Prototyp).

## Checkliste

- [x] Validator-Erweiterung (Komponenten-Rollen, Familien-Heuristik aus Manifest)
- [x] Manifest-Einträge (Quellen, Hashes, Varianten, VRAM-Werte aus §12.3/§12.4)
- [x] VRAM-Detection + Empfehlungs-Logik
- [x] Bind-Dialog-Erweiterung (Mehrfach-Picker) + Download-Dialog (Varianten-Wahl)
- [x] Tests: Vollständigkeits-Gate, Mismatch-Warnung
- [x] Doc-Update: routes.md, README Modell-Sektion

## Report-Back

### 2026-06-23 — Phase 2 abgeschlossen

**Backend:**
- `validation.py`: Komponenten-Validierung (`validate_component_model`), Familien-Erkennung, safetensors/gguf-Probes
- `vram.py`: GPU-Erkennung (torch.cuda + nvidia-smi Fallback), Varianten-Empfehlung
- `api/models.py`: `register-local` akzeptiert `path` oder `components`, gibt `{model, warnings[]}` zurück; neuer `GET /api/models/vram`
- `loader.py`: ManifestEntry parst `component_model`, `components`, `variants`, `expected_families`
- `manifest.json`: Flux-Einträge mit Komponenten-Specs, Varianten, erwarteten Familien
- 16 Backend-Tests bestanden (5 neue Komponenten-Tests)

**Frontend:**
- Bind-Dialog: Erkennt Komponenten-Modelle, zeigt Multi-Picker, Warnungen, Completeness-Gate
- Download-Dialog: Varianten-Auswahl mit VRAM-basierter Empfehlung
- Model-Drawer: Zeigt Komponenten-Pfade statt Einzel-Pfad
- Modelle-Shell: GPU-Systembar, VRAM-Dispatch, neue Actions/Effects/Selectors
- Types: `VramResponse`, `VariantSpec`, `ComponentSpec`, `RegisterLocalResponse`
