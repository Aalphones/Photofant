# STATE

**Aktiver Plan:** `docs/planning/2026-07-20_lightbox-tabbed-panel.md` — beide Phasen ✅ complete,
`ng build` grün. **Noch offen:** User-Smoke-Test (Checkliste steht im Plan, Wackelstellen
zuerst), danach Archivieren.
**Nächster Schritt:** Nach grünem Smoke-Test archivieren (`git mv` → `docs/archive/2026-07/`),
danach weiter mit P35 Phase 2/3 (siehe Backlog unten).

## Backlog — P35 (Phase 1 committet, Phase 2 offen)

Plan `docs/planning/2026-07-20_p35-gemma-gguf-runtime/` — Phase 1/3 (GGUF-Runtime + Adapter +
VRAM-Koordination) ✅ complete **und committet** (`1ac7d01`). Nächster Schritt: Phase 2/3
(Format-Routing + Manifest-Eintrag + In-Place-Bind, Komplexität: standard, Modell-Empfehlung:
`sonnet`).

## Phase 1 erledigt (GGUF-Runtime + Adapter + VRAM-Koordination)

`inference/gguf_engine.py` neu (`GgufEngine`, Lifecycle-Form gespiegelt von
`GenerativeEngine`), `inference/adapters/gemma_gguf.py` neu (`GemmaGgufAdapter` +
`GemmaGgufVisionAdapter` — zwei Klassen statt Instanz-Flag, Begründung in der
Phasen-Datei), `VisionTextGenerator`-Protocol in `interfaces.py`, Cross-Unload in
beide Richtungen (`generative_engine.py` ↔ `gguf_engine.py`, ADR-029), Idle-Loop +
Shutdown in `main.py` um den GGUF-Slot erweitert, neue Extra-Group `gemma-gguf` in
`pyproject.toml`. ruff grün (neue/geänderte Dateien), mypy grün bis auf den
erwarteten `llama_cpp`-Import-Fehler (Paket noch nicht installiert — Smoke #1
installiert es). ADR-029 angelegt. **Noch offen: Backlog P27-Smoke + Archivieren**
(siehe unten) — unabhängig von P35, wartet weiter auf den User.

## Backlog — P27 (parkt, nicht blockierend für P35)

Plan `docs/planning/2026-07-01_p27-gemma-integration/` — alle 4 Phasen ✅ complete,
Plan-Ende offen: (1) User-Smoke (Checkliste in der README, Wackelstellen zuerst) —
Gemma muss dafür geladen/verfügbar sein; (2) Archivieren nach grünem Smoke
(`git mv` → `docs/archive/2026-07/`, README-Bottom-Sektionen füllen).

## Backlog (nach P35)

- `docs/planning/2026-07-06_p34-mcp-wissensbasis/` — blockiert bis MCP-Basisplan + P27 stehen.

## Smoke-Test P26 ausstehend (User)

Real-Check der Empfehlungs-Engine — Details:
`docs/archive/2026-07/2026-07-01_p26-recommendation-engine/README.md`.
