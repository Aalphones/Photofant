# FINDINGS — P33 pHash-Ablösung

> Erkenntnisse während der Umsetzung, getaggt auf die Phase, die sie betreffen.
> Format: `- [ ] → Phase N: <Erkenntnis, 1-3 Zeilen — was wurde entdeckt, was heißt das für die Ziel-Phase>`

- [x] → Phase 2: `dupe_threshold` in `settings.py` bleibt entgegen Phase-1-AK-4 bewusst erhalten — `api/collections.py` `/duplicates` (Trainingsset-pHash-Suche, Fence-Funktion #3) liest ihn noch und würde sonst mit KeyError crashen. Beim Umbau dieses Endpoints auf CLIP in Phase 2 den Key final aus Dataclass/Defaults/`_EXPECTED_TYPES` entfernen. → erledigt: `dupe_threshold` komplett aus `settings.py` (+ `settings.example.json`) entfernt.
