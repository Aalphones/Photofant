# P7 · Phase 3 — Person-Ordner & Kopien

> Rating: **heikel** (physische Kopien/Moves über mehrere Dateien + DB in einem logischen Schritt — Kernrisiko des Datenmodells) · Status: pending

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (assign)
- [Konzept](../../Konzept-Photofant.md) §4.1–4.3 (Kopien, Moves), §6.1 Schritt 8, §6.1a (FS-Drop), §7 (manuelle Korrektur)
- Move-Modul aus P2 Phase 5 + Reconciliation aus P3 (Sicherheitsnetz)

## Akzeptanzkriterien

- Zuordnung erzeugt Person-Ordner (`personX/photos|favourites|faces|edits`) + echte Kopie pro Person; `asset_instance` pro (Asset, Person) mit Pfad; `_unknown`-Instanz wird zur ersten echten Person **verschoben**, weitere Personen erhalten **Kopien**.
- Manuelle Korrektur (`PATCH /api/faces/{id}/assign`): Bilddatei + zugehörige Face-Crops + Edits ziehen physisch um; alle DB-Pfade nachgeführt; Smart-Album-Hook (P6) feuert.
- FS-Drop (§6.1a): Scan erkennt Dateien in Person-Ordnern ohne DB-Eintrag → Verarbeitung mit `fixed_person = true`; weitere erkannte Personen → Kopien, fixe Zuordnung unangetastet.
- Crash-Sicherheit: Multi-Datei-Operationen laufen als geordnete Einzel-Moves über das Move-Modul; Abbruch hinterlässt einen Zustand, den der P3-Reconcile als Drift findet und reparieren kann (dokumentierte Wiederanlauf-Strategie statt Pseudo-Transaktion).

## Checkliste

- [ ] Ordner-Anlage + Kopier-/Move-Orchestrierung (Erst-Person = Move, weitere = Copy)
- [ ] assign-Endpoint (Bild + Faces + Edits umziehen, `fixed_person` setzen)
- [ ] FS-Drop-Erkennung im Scan-Job (Ziel-Person aus dem Ordnerpfad)
- [ ] Favoriten-Move (P2) auf Person-Ordner verallgemeinern
- [ ] Tests: Korrektur-Szenario (Multi-Datei), Gruppenbild-Kopien, FS-Drop mit Zweit-Person — datenkritisch
- [ ] Doc-Update: docs/models.md (Instanz-Semantik), routes.md

## Report-Back
