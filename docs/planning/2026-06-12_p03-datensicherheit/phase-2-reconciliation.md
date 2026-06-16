# P3 · Phase 2 — FS↔DB-Reconciliation

> Rating: **heikel** (Klassifikations-Logik; falsche Repair-Aktion kann Daten kosten) · Status: complete

## Kontext (vorher lesen)

- [README.md](README.md) — Kontrakt (Report-Form, Repair-Actions)
- [Konzept](../../Konzept-Photofant.md) §13.2, §4 (Pfad-Führung in der DB)
- Move-Modul aus P2 Phase 5 (Wiederverwendung für `fix_path`)

## Akzeptanzkriterien

- Scan vergleicht `Data/`-Bestand gegen `asset_instance.path`: **verwaist** (FS ohne DB), **fehlend** (DB ohne FS), **Drift** (Datei woanders gefunden — Match über Content-Hash).
- Drift-Erkennung rehasht nur Kandidaten (Dateiname/Größe-Vorfilter), nicht die ganze Bibliothek; Fortschritt über die Queue.
- Repair-Aktionen: verwaist → neu indizieren (Import-Pfad) oder Papierkorb; fehlend → als fehlend markieren (UI-Kennzeichnung) oder Eintrag in Papierkorb; Drift → Pfad korrigieren.
- Report bleibt bis zum nächsten Scan abrufbar; keine Repair-Aktion läuft ohne explizite Auswahl (kein Auto-Repair).

## Checkliste

- [x] Scan-Job (Walk über `Data/`, Abgleich, Vorfilter + gezieltes Rehashing)
- [x] Report-Persistenz (app_config oder eigene Tabelle) + Endpoints
- [x] Repair-Endpoint, der pro Item die gewählte Aktion ausführt (Move-Modul nutzen)
- [x] Unit-Tests für die Klassifikation (drei Fälle + Hash-Match) — datenkritisch, siehe testing.md
- [x] UI: Report-Tabelle mit Aktions-Auswahl pro Zeile + „Ausführen"
- [x] Doc-Update: routes.md

## Report-Back

**Backend**
- `photofant/maintenance/reconcile.py` — pure Klassifikations-Kern `classify_reconcile()`: 3-Wege-Abgleich (verwaist/fehlend/Drift). Drift nur per **echtem SHA-256-Hash** bestätigt, Kandidaten über **Dateigrößen-Vorfilter** (kein Rehash der ganzen Bibliothek). Bewusst seiteneffektfrei → unit-testbar.
- `photofant/maintenance/store.py` — Report als JSON-Blob unter `app_config['reconcile_report']` (kein eigenes Table; Wegwerf-Snapshot).
- `photofant/maintenance/repair.py` — Einzelaktionen `trash_orphan` / `mark_missing` / `purge_missing` / `fix_drift`, jede mit **`ensure_under_root`-Pfadwache** (kein Repair außerhalb der Data-Root — datenkritisch).
- `photofant/jobs/reconcile_job.py` — Scan-Job (`os.walk`, `.photofant/`-Subtree ausgeschlossen), neue `JobKind.RECONCILE`.
- `photofant/api/maintenance.py` — `POST /reconcile`, `GET /reconcile/report`, `POST /reconcile/repair` (bündelt `orphan→index` in **einen** Import-Job).
- Migration `0003` + `AssetInstance.missing_at`.
- Tests: `tests/test_reconcile.py` (8 Fälle: 3 Buckets, Hash-Drift, Größen-/Inhalts-Negativfälle, Pfadwache). Gesamt 20 Backend-Tests grün, ruff sauber.

**Frontend**
- Models/Service/NgRx-Slice (Reconcile-Report + Repair) erweitert; `reconcile`-JobKind ergänzt.
- Reconcile-Effekt lauscht auf Job-Stream (`reconcile` done → Report nachladen); Repair entfernt erledigte Zeilen optimistisch.
- `Einstellungen`-View: Scan-Button + Status + Tabs (Verwaist/Fehlend/Drift) + Repair-Buttons pro Zeile. Lint + Build grün.

**Abweichungen vom Kontrakt**
- Repair-Aktion `"trash"` ist kontextabhängig: orphan → Datei in Papierkorb verschieben; missing → DB-Zeile purgen (Datei ist eh weg). UI-Label „DB-Eintrag löschen" für missing.
- Design-Prototyp `maintenance.jsx` ist eine eigene „Wartung"-Seite mit Status-Leiste + Rebuild-Ops — die UI lebt aber laut Kontrakt unter **Einstellungen**. Status-Leiste + Rebuilds gehören zu Phase 3 (Wartungs-View). → FINDINGS.
- Kein Bulk-Select (Prototyp hat Checkboxen) — AK verlangt nur „pro Zeile + Ausführen". Bulk ist optionaler Phase-3-Komfort.
