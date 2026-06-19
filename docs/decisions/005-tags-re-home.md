# ADR-005 — Schicksal der Tags-Seite

**Status:** accepted  
**Datum:** 2026-06-19  
**Plan:** `docs/planning/2026-06-19_design-angleichung/` Phase 3

## Kontext

Die `/tags`-Route (Tag-Verwaltung) wurde im Rahmen von P6 gebaut. Das Design reserviert nur
einen Nav-Slot (`app.jsx:63`), zeichnet den Screen aber nie aus — die Optik wurde freihändig
erfunden. Die Seite ist funktional vollständig: Suche, Tabellen-Liste, Umbenennen, Merge/Alias,
Bulk-Auswahl.

Drei Optionen standen zur Wahl:  
**(A)** Eigenes Mockup nachziehen und Impl daran ausrichten.  
**(B)** Tag-Verwaltung in die Einstellungen einfalten, `/tags`-Route entfernen.  
**(C)** Seite behalten, nachträglichen Design-Eintrag schreiben, auf Primitive umstellen.

## Entscheidung

**Option (B) — Re-home in Einstellungen.**

Die standalone `/tags`-Route entfällt. Die gesamte Funktionalität
(Suche, Umbenennen, Merge, Alias-Anzeige) lebt als neue Sektion `tags` innerhalb der
Einstellungen-Shell.

## Begründung

- Der User hat keine eigenständige Seite gewünscht: „kann ersatzlos entfernt werden".
- Die Einstellungen sind der natürliche Ort für globale Verwaltungs-Operationen
  (Datenbank-Backup, Modelle, Presets — jetzt auch Tag-Pflege).
- Re-home ist weniger Aufwand als (A) und sauberer als (C), das den Status quo nur legitimiert.
- Die Funktionalität bleibt vollständig erhalten — kein Datenverlust, kein Merge-Verlust.

## Konsequenzen

- `frontend/src/app/features/tags/` gelöscht.
- Route `{ path: 'tags' }` entfernt aus `app.routes.ts`.
- Nav-Rail-Eintrag `{ id: 'tags' }` entfernt aus `nav-rail.ts`.
- Einstellungen: neue Sektion `tags` mit Icon `tag`, Label `Tags`.
- `docs/routes.md`: Tags-Endpoints jetzt unter `/einstellungen` gelistet.
