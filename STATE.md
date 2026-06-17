# STATE — Photofant

> Kanonischer Resume-Pointer für laufende Implementierung. Wird bei jeder Phasengrenze aktualisiert, **nie** gelöscht.

## Aktiver Plan

**P4 — Modell-Management** · [`docs/planning/2026-06-12_p04-modell-management/`](docs/planning/2026-06-12_p04-modell-management/README.md)

## Stand

| Phase | Topic | Status |
|---|---|---|
| 1 | Registry & Manifest | ✅ complete |
| 2 | Download & Scan | ✅ complete |
| 3 | In-Place-Binding & Validierung | ✅ complete |
| 4 | Modelle-View & Gating | 🔲 pending |

## Nächster Schritt

→ **Phase 4 starten** — Modelle-View & Gating (Angular `/einstellungen`: Modell-Liste, Download-Buttons, In-Place-Picker, Feature-Gating über `GET /api/models/capabilities`).
Einstieg: [`docs/planning/2026-06-12_p04-modell-management/phase-4-modelle-view-gating.md`](docs/planning/2026-06-12_p04-modell-management/phase-4-modelle-view-gating.md)

Rating: standard → `/clear`, dann `/model sonnet` reicht für Phase 4 (Frontend, kein `ng test` im private-Profil).
