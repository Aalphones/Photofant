# FINDINGS — P18 Bildklassifizierung

> Während der Umsetzung entdeckte Abweichungen/Erkenntnisse, getaggt nach Phase.
> Format: `- [ ] → Phase N: <Erkenntnis / nötige Anpassung>`

- [ ] → Phase 3: SQLite erzwingt `ON DELETE CASCADE` nur bei aktivem
  `PRAGMA foreign_keys=ON` — dieses Pragma wird in `db/engine.py` aktuell **nicht**
  gesetzt (projektweit, nicht neu). Die deklarierten Cascades auf
  `classification_label.category_id` und `asset_classification.label_id` räumen also
  beim `DELETE /classification/categories/{id}` bzw. `.../labels/{id}` **nicht**
  automatisch auf — Phase 3 muss die Kind-Zeilen explizit im Python-Code löschen
  (oder das Pragma global aktivieren, was breiter wirkt als diese Phase).
