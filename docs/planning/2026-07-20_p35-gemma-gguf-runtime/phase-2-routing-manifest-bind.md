# Phase 2 — Format-Routing + Manifest-Eintrag + In-Place-Bind

**Komplexität:** standard · **Status:** pending

## Kontext (lesen, bevor du baust)
- [inference/capabilities.py:62-66](../../../backend/photofant/inference/capabilities.py#L62) — `resolve_generator`, die Format-Weiche kommt hierher.
- [models/manifest.json:342-354](../../../backend/photofant/models/manifest.json#L342) — der bestehende `gemma-3-4b-it`-Eintrag als Vorlage; der neue GGUF-Eintrag steht daneben.
- [models/validation.py:152-157](../../../backend/photofant/models/validation.py#L152) — der GGUF-Zweig existiert bereits (SINGLE_FILE-Layout), nichts daran ändern.
- [api/models.py](../../../backend/photofant/api/models.py) — der In-Place-Bind-Pfad (wie ein Modell einen `ModelRegistry.path` bekommt); nur lesen, um den Bind-Weg zu kennen — kein Code-Change nötig, wenn der Bind über die bestehende UI/Route läuft.
- [docs/models.md](../../../docs/models.md) — Manifest-Feld-Doku.

## AK der Phase
- [ ] `resolve_generator` gibt für ein Modell mit Manifest-`format == "gguf"` einen `GemmaGgufAdapter` zurück, sonst (safetensors) den bestehenden `GemmaAdapter` — der Aufrufer `generate` bleibt unverändert.
- [ ] Manifest-Eintrag fürs 12B-GGUF vorhanden, `format: "gguf"`, `role: "text_generator"`, `requires_license_ack` gesetzt (abliteriertes Modell — Lizenz/Herkunft bewusst bestätigen). Der Eintrag führt den **mmproj als optionale zweite Datei** (Vision-Naht), sodass `resolve_gemma_gguf` den mmproj-Pfad findet, wenn er mitgebunden ist.
- [ ] Das lokale GGUF (`D:\Models\OBLITERATUS\Gemma-4-12B-OBLITERATED\Gemma-4-12B-OBLITERATED-Q4_K_M.gguf`) ist als In-Place-Bind mit `enabled=True` in der `ModelRegistry` bindbar; `resolve_gemma_gguf` findet den Pfad.
- [ ] `ai.gemmaModel` (bzw. `ai.capabilityMap`) kann auf den neuen Manifest-Eintrag zeigen — Umschalten safetensors↔gguf ist reine Settings-/Bind-Sache.

## Checkliste
- [ ] `capabilities.py`: `resolve_generator` verzweigt nach Manifest-`format`. Den `format` aus dem gebundenen `ModelRegistry`/Manifest lesen (nicht raten). Bei unbekanntem Format: `None` + Log-Warnung (graceful, wie der Rest der Schicht).
- [ ] `models/manifest.json`: neuer Eintrag, z.B. `id: "gemma-3-12b-obliterated-gguf"`, `format: "gguf"`, `variant: "in_place"`, `files: [{ "filename": "Gemma-4-12B-OBLITERATED-Q4_K_M.gguf" }, { "filename": "mmproj-BF16.gguf", "optional": true, "role": "mmproj" }]`, `requires_license_ack: true`, `tier: "generativ"`. Die mmproj-Datei ist optional — fehlt sie, ist der Adapter reiner Text. **Kein Binary ins Repo** (Critical Rule 4) — nur der Manifest-Eintrag. **Prüfen:** ob der bestehende GGUF-Validierungszweig ([validation.py:152](../../../backend/photofant/models/validation.py#L152), SINGLE_FILE) eine zweite optionale Datei toleriert; falls er auf genau eine Datei besteht, minimal-invasiv um optionale Zusatzdatei erweitern (nicht die SINGLE_FILE-Semantik der Hauptdatei brechen).
- [ ] Bind durchführen bzw. den Bind-Weg dokumentieren (In-Place über die Modell-Verwaltung auf den D:\-Pfad). Läuft der Bind über die bestehende UI/Route → kein Code, nur im Report-Back den Weg notieren.
- [ ] `cd backend && uv run ruff check . && uv run mypy photofant/inference/capabilities.py` grün.

## Report-Back
