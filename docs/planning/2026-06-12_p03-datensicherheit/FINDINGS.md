# FINDINGS — P3 Datensicherheit

> Erkenntnisse während der Umsetzung, getaggt auf die Phase, die sie betreffen. Format:
> `- [ ] → Phase N: <Erkenntnis>`

- [x] → Phase 3: Der Design-Prototyp `docs/design/js/maintenance.jsx` ist eine **eigene „Wartung"-Seite** mit Status-Leiste (letzter Scan, db.sqlite-Größe, Thumbnail-/Face-Count) + den Rebuild-Ops. Phase 2 hat nur die Scan-/Repair-Sektion in `Einstellungen` gebaut. Phase 3 entscheidet: Status-Leiste + Rebuilds dort anbauen oder in eine eigene `wartung`-Route ziehen (dann Reconcile-Sektion mitnehmen). Bulk-Select (Checkboxen im Prototyp) ist optionaler Komfort.
  → **Entschieden (User):** eigene `/wartung`-Route nach Prototyp; Scan-/Repair-Sektion aus `Einstellungen` rübergezogen, **Backup bleibt** in `Einstellungen` (Prototyp zeigt dort kein Backup). Bulk-Select weggelassen (optionaler Komfort, nicht in den AK).
- [x] → Phase 3: Reconcile scannt aktuell den **ganzen** `Data/`-Baum (außer `.photofant/`) und kennt nur `asset_instance` (photos/favourites). `faces/`- und `edits/`-Dateien hätten keine DB-Zeile und würden als „verwaist" gemeldet — heute leer, aber P7/P8 müssen reconcile um Face-/Edit-Tabellen erweitern. Für Phase 3 (Thumbnail-/Face-Rebuild) nur relevant, falls Rebuild Crops in `faces/` ablegt.
  → **Kein Impact für Phase 3:** Thumbnail-Rebuild schreibt ausschließlich in `thumbnails.sqlite`, fasst `faces/` nicht an. Carry-over bleibt für **P7/P8** (Face-Rebuild + reconcile um Face-/Edit-Tabellen erweitern) — beim Anlegen des P7-Plans aufgreifen.
