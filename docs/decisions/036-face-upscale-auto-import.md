# ADR-036 — Face-Upscale erzeugt eine face-gebundene Version, kein neues Asset

**Status:** Akzeptiert — 2026-07-23
**Querverweise:** [013](013-comfyui-edit-als-asset.md) (Asset-Auto-Import, das Gegenstück für
Foto-Ziele), [033](033-face-cleanup-score-on-demand.md) (Face.is_upscaled im Cleanup-Score)

## Kontext
Der bestehende ComfyUI-Bulk-Auto-Import (`run_default_workflow`) kennt nur Asset-Ziele und legt
für jedes Ergebnis ein komplett neues `Asset` an (ADR-013) — passend für „ganzes Foto
hochskalieren", aber falsch für „Gesichts-Crop hochskalieren": es gibt kein Asset, das den
hochskalierten Crop sinnvoll repräsentiert, und `Face.is_upscaled` (fließt in den Cleanup-Score
ein) würde nie berührt.

## Entscheidung
Face-Upscale-Ergebnisse werden als neue **face-gebundene `Version`** gespeichert (dasselbe Muster
wie der Crop-Editor-Speicherpfad in `edit_sessions.py`), nicht als neues Asset. Der Editor-Pfad
und der neue Auto-Import-Pfad teilen sich seither dieselben Helfer
(`photofant/media/versions.py`), damit beide nicht auseinanderdriften. Das zugehörige `Face`
bekommt `is_upscaled = True`.

## Betrachtete Optionen
- **Asset-Auto-Import auf die Quell-Fotos der ausgewählten Gesichter umleiten** — kein neuer
  Auto-Import-Pfad nötig, aber upscaled das ganze Foto statt des Crops, berührt
  `Face.is_upscaled` nie, und funktioniert nicht für Gesichter ohne Quell-Foto
  (`Face.asset_id IS NULL`). Verworfen — vom User explizit gegen diese günstigere Variante
  entschieden (siehe Plan-README „Vorgeschichte").
- **Neues Asset auch für Face-Ergebnisse** (Wiederverwendung von `import_comfyui_output`) — hätte
  ein Asset ganz ohne zugehöriges Foto im Bestand erzeugt (keine `AssetInstance`,
  kein `original_id`-Ziel im bisherigen Sinn) — verworfen, verletzt die Asset-Invariante „ein
  Asset hat mindestens eine Instanz".

## Konsequenzen
- Face-Upscale ist der erste und einzige Ort im Bestand, der `Face.is_upscaled` auf `True` setzt.
- `edit_sessions.py` und `comfyui_run_job.py` teilen sich jetzt `photofant/media/versions.py` —
  künftige Änderungen am Version-Anlage-Muster (z. B. neue Pflichtfelder) müssen an **einer**
  Stelle gepflegt werden, nicht zwei.
