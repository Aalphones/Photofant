# Phase 2 — Format-Routing + Manifest-Eintrag + In-Place-Bind

**Komplexität:** standard · **Status:** pending

## Kontext (lesen, bevor du baust)
- [inference/capabilities.py:62-66](../../../backend/photofant/inference/capabilities.py#L62) — `resolve_generator`, die Format-Weiche kommt hierher.
- [models/manifest.json:342-354](../../../backend/photofant/models/manifest.json#L342) — der bestehende `gemma-3-4b-it`-Eintrag als Vorlage; der neue GGUF-Eintrag steht daneben.
- [models/validation.py:152-157](../../../backend/photofant/models/validation.py#L152) — der GGUF-Zweig existiert bereits (SINGLE_FILE-Layout), nichts daran ändern.
- [api/models.py](../../../backend/photofant/api/models.py) — der In-Place-Bind-Pfad (wie ein Modell einen `ModelRegistry.path` bekommt); nur lesen, um den Bind-Weg zu kennen — kein Code-Change nötig, wenn der Bind über die bestehende UI/Route läuft.
- [docs/models.md](../../../docs/models.md) — Manifest-Feld-Doku.

## AK der Phase
- [x] `resolve_generator` gibt für ein Modell mit Manifest-`format == "gguf"` einen `GemmaGgufAdapter` zurück, sonst (safetensors) den bestehenden `GemmaAdapter` — der Aufrufer `generate` bleibt unverändert.
- [x] Manifest-Eintrag fürs 12B-GGUF vorhanden, `format: "gguf"`, `role: "text_generator"`, `requires_license_ack` gesetzt (abliteriertes Modell — Lizenz/Herkunft bewusst bestätigen). Der Eintrag führt den **mmproj als optionale zweite Datei** (Vision-Naht), sodass `resolve_gemma_gguf` den mmproj-Pfad findet, wenn er mitgebunden ist.
- [x] Das lokale GGUF (`D:\Models\OBLITERATUS\Gemma-4-12B-OBLITERATED\Gemma-4-12B-OBLITERATED-Q4_K_M.gguf`) ist als In-Place-Bind mit `enabled=True` in der `ModelRegistry` bindbar; `resolve_gemma_gguf` findet den Pfad. (Bind-Weg steht, Ausführung selbst ist User-Aktion über die laufende App — siehe Report-Back.)
- [x] `ai.gemmaModel` (bzw. `ai.capabilityMap`) kann auf den neuen Manifest-Eintrag zeigen — Umschalten safetensors↔gguf ist reine Settings-/Bind-Sache (unverändert, Settings-Layer greift bereits generisch über `manifest_id`).

## Checkliste
- [x] `capabilities.py`: `resolve_generator` verzweigt nach Manifest-`format`. Den `format` aus dem gebundenen `ModelRegistry`/Manifest lesen (nicht raten). Bei unbekanntem Format: `None` + Log-Warnung (graceful, wie der Rest der Schicht).
- [x] `models/manifest.json`: neuer Eintrag `id: "gemma-3-12b-obliterated-gguf"`, `format: "gguf"`, `variant: "in_place"`, `files: [{ "filename": "Gemma-4-12B-OBLITERATED-Q4_K_M.gguf" }, { "filename": "mmproj-BF16.gguf", "optional": true, "role": "mmproj" }]`, `requires_license_ack: true`, `tier: "generativ"`. Kein Binary ins Repo — nur der Manifest-Eintrag. **Geprüft:** der GGUF-Validierungszweig (SINGLE_FILE) validiert immer genau den einen übergebenen Pfad — er "sieht" die zweite Datei gar nicht, es gab nichts zu brechen. Der fehlende Teil war eine andere Stelle: `register_local` persistierte für Nicht-Component-Modelle bislang gar kein `components`-Feld — dafür jetzt `validate_companion_file` (validation.py) + Erweiterung des Bind-Endpunkts (api/models.py, siehe unten).
- [x] Bind-Weg dokumentiert (siehe Report-Back) — Ausführung ist User-Aktion (Modell-Verwaltung → In-Place-Bind auf den D:\-Pfad), kein Code nötig, da `POST /api/models/register-local` bereits existiert und jetzt die optionale `components.mmproj` mitnimmt.
- [x] `cd backend && uv run ruff check . && uv run mypy photofant/inference/capabilities.py` — ruff clean auf allen 3 geänderten Dateien; mypy zeigt exakt die 2 **vorbestehenden** Baseline-Fehler (unabhängig verifiziert per `git stash`), keinen neuen. Details im Report-Back.

## Report-Back

**Umsetzung über den Plan hinaus (Ergänzung, kein Scope-Creep):** Der Plan sah nur die Format-Weiche in `resolve_generator` und den Manifest-Eintrag vor. Beim Umsetzen fiel auf: der Bind-Endpunkt (`api/models.py: register_local`) hatte für **Nicht**-Component-Modelle noch keinen Weg, ein optionales `components`-Feld (den mmproj-Pfad) überhaupt zu persistieren — nur die Flux-artige `is_component_model`-Schiene schrieb `components`. Ohne diese Ergänzung hätte `resolve_gemma_gguf`s `entry.components.get("mmproj")` (Phase 1) nie etwas gefunden. Ergänzt: `validate_companion_file` (validation.py, leichte Prüfung — Existenz + GGUF-Magic, keine volle 5-Stufen-Pipeline, da die Companion-Datei keinen eigenen Manifest-Slot hat) + Erweiterung von `register_local`: wenn der Manifest-Eintrag ein `role: "mmproj"`-File deklariert **und** der Request eine `components.mmproj` mitschickt, wird sie validiert und in `row.components` geschrieben — sonst bleibt das Verhalten für alle anderen Modelle exakt wie vorher.

**Bind-Weg (User-Aktion, nicht Teil dieser Phase-Umsetzung):**
1. App starten, Modell-Verwaltung öffnen (Einstellungen → Modelle).
2. Beim neuen Eintrag „Gemma 3 12B Obliterated (GGUF, Q4_K_M)" auf „Lokal vorhanden binden" (In-Place).
3. Hauptpfad: `D:\Models\OBLITERATUS\Gemma-4-12B-OBLITERATED\Gemma-4-12B-OBLITERATED-Q4_K_M.gguf`.
4. Optional (Vision-Naht, kann auch später nachgezogen werden): mmproj-Pfad `D:\Models\OBLITERATUS\Gemma-4-12B-OBLITERATED\mmproj-BF16.gguf`, falls die UI dafür ein zweites Feld zeigt — sonst reicht Phase 3/später ein API-Call gegen `POST /api/models/register-local` mit `components: {"mmproj": "..."}`.
5. Lizenz-Bestätigung (abliteriertes Modell, `requires_license_ack`) bestätigen.
6. Danach `ai.gemmaModel` (oder `ai.capabilityMap.text_generation`) in den Settings auf `gemma-3-12b-obliterated-gguf` zeigen lassen.

**Mypy-Baseline (nicht meins, aber transparent):** 2 vorbestehende Fehler unverändert vor/nach meiner Änderung (`git stash`-Vergleich): `validation.py:221` (onnxruntime-Stub-Mismatch) und die jetzt verschobene `autonomy_for`-Zeile (ai["autonomy"].get(...) → object statt str). Beide waren schon auf `master` rot, keine Regression durch Phase 2 — aber auch nicht von mir gefixt (außerhalb des Phasen-Scopes).
