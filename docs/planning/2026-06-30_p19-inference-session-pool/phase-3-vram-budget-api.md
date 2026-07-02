# Phase 3 — VRAM-Budget-Rechner + API-Erweiterung

**Rating:** mechanisch (reine Formel + bestehenden Endpoint um zwei Felder erweitern)

## Kontext (vor dem Start lesen)

- `backend/photofant/models/vram.py` — komplette Datei (100 Zeilen): `detect_gpu()`,
  `GpuInfo`-Dataclass, `recommend_variant()`. Neue Funktionen kommen als weitere
  Modul-Funktionen dazu, gleiches Stilmuster (reine Funktion, `float | None`-Eingabe robust
  behandeln).
- `backend/photofant/api/models.py` Zeile 386-424 — `GpuInfoDto`, `VramRecommendation`,
  `VramResponse`, `get_vram()`. Hier werden die zwei neuen Felder ergänzt.
- `frontend/src/app/models/model.model.ts` Zeile 40-54 — `GpuInfoDto`, `VramRecommendation`,
  `VramResponse` (TS-Pendant, muss synchron zum Backend-DTO gehalten werden).

## Formeln (aus der ursprünglichen Skizze übernommen)

```python
def suggest_tagging_workers(vram_gb: float) -> int:
    # WD14 SwinV2-v3: ~450 MB pro Session-Instanz + ~200 MB Aktivierungen pro Lauf
    available = vram_gb - 1.5  # OS + andere Modelle
    return max(1, min(4, int(available / 0.65)))

def suggest_captioning_workers(vram_gb: float) -> int:
    # Florence-2-base: ~1.5 GB pro Session-Instanz (4 ONNX-Sessions) + ~300 MB Aktivierungen
    available = vram_gb - 0.5  # OS
    return max(1, min(4, int(available / 1.8)))
```

Beispiel RTX 3060 (12 GB): Tagging → 4 (gedeckelt), Captioning → 4 (gedeckelt, roh 6).

## Akzeptanzkriterien

1. `suggest_tagging_workers`/`suggest_captioning_workers` in `vram.py`, Rückgabe immer
   `1 <= n <= 4`.
2. `GET /api/models/vram` liefert zusätzlich `suggested_tagging_workers`,
   `suggested_captioning_workers` — `null`, wenn `detect_gpu()` `None` liefert (kein GPU
   erkannt), sonst die berechneten Werte.
3. Frontend-`VramResponse`-Typ hat die zwei neuen optionalen Felder, konsistent zum Backend-DTO.
4. Manueller Check: `curl /api/models/vram` (oder Swagger-UI) zeigt die neuen Felder mit
   plausiblen Werten für die eigene GPU.

## Checkliste

- [ ] `suggest_tagging_workers`/`suggest_captioning_workers` in `vram.py`
- [ ] `GpuInfoDto`/`VramResponse` in `api/models.py` erweitert, `get_vram()` befüllt die Felder
- [ ] `VramResponse`-TS-Typ in `model.model.ts` synchron erweitert
- [ ] Manueller Endpoint-Check (curl/Swagger) mit echten Werten

## Report-Back
