# P29 — Personen durchsuchen, filtern, gruppieren

**Status:** pending

Personen-Tab wird bei vielen Personen unübersichtlich. Freitext-Gruppen (z.B.
„Familie", „Freunde"), Schnellsuche, Sortierung und ein View-Toggle
(Einzelfoto / 4er-Grid / Gesichtsausschnitt) machen ihn wieder schnell
erfassbar. Zusätzlich wandert der bestehende Clustering-Trigger aus den
Einstellungen auch auf die Personen-Seite (bestehende Store-Actions, reines
UI-Wiring).

---

## Overview

| Phase | Thema | Tier | Status |
|---|---|---|---|
| 1 | Backend — Gruppenfeld + Erstellungsdatum | standard | pending |
| 2 | Frontend Store — Persistenz für Gruppen-Zuweisung | standard | pending |
| 3 | Frontend UI — Toolbar, Grid, Karte, Clustering-Button | standard | pending |
| 4 | Politur — Zusatz-Sortierungen, Empty-States, Perf-Check | standard | pending |

---

## Kontrakt (Cross-Modul-Ankerpunkt)

### Backend (Phase 1 — models.py + persons.py)

```python
# db/models.py — Person
group_name: Mapped[str | None] = mapped_column(Text, nullable=True)
created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

Neue Alembic-Migration fügt beide Spalten hinzu. Bestehende Personen bekommen
`created_at = NULL` (kein Backfill — Sortierung behandelt NULL als „ältest").
Neue Personen (`create_person`) setzen `created_at = datetime.now(UTC)`.

```python
# api/persons.py — PersonDto erweitert
group_name: str | None
created_at: datetime | None

# PATCH /persons/{id} — RenameRequest → UpdatePersonRequest
class UpdatePersonRequest(BaseModel):
    name: str | None = None
    group_name: str | None = None
```
Mindestens eines der beiden Felder muss gesetzt sein (422 sonst). Leerstring
bei `group_name` löscht die Gruppe (→ `None`).

### Frontend — PersonDto (Phase 2)

```typescript
// models/person.model.ts
export interface PersonDto {
  id: number;
  name: string | null;
  is_unknown: boolean;
  count: number;
  fav_count: number;
  portrait_face_id: number | null;
  group_name: string | null;   // neu
  created_at: string | null;   // neu — ISO-String
}
```

### Frontend — neue NgRx-Action (Phase 2)

```typescript
// persons.actions.ts — neu
'Set Person Group':         props<{ id: number; groupName: string | null }>()
'Set Person Group Success': props<{ person: PersonDto }>()
'Set Person Group Failure': props<{ error: string }>()
```
Reine Persistenz-Aktion — Suche/Sortierung/View-Modus sind **kein** Store-State
(siehe Risiken unten), sondern lokale Signals in `Personen`.

### Frontend — Clustering-Button (Phase 3)

Wiederverwendet **1:1** bestehende Infrastruktur, keine neuen Actions:
```typescript
this.store.dispatch(personsActions.triggerClustering());
this.store.selectSignal(personsSelectors.selectIsClustering);
```

---

## Finale Abnahme-Kriterien

- [ ] Person bekommt eine Freitext-Gruppe zugewiesen → bleibt nach Reload erhalten
- [ ] Schnellsuche filtert die Personen-Liste live nach Namen
- [ ] Sortier-Icon zykelt Gruppe → Erstellungsdatum → Name (A-Z)
- [ ] Personen werden gruppiert mit Section-Headern angezeigt (Stil wie Monats-Header in der Galerie), inkl. „Ohne Gruppe"-Bucket
- [ ] Gruppen sind als Filter-Chips wählbar (Mehrfachauswahl)
- [ ] View-Toggle schaltet zwischen Einzelfoto / 4er-Grid / Gesichtsausschnitt um
- [ ] „Clustering starten" ist auch auf der Personen-Seite verfügbar und nutzt den bestehenden Job-Flow
- [ ] Bereits benannten/zugewiesenen Gesichtern passiert beim Clustering nichts (verifiziert — siehe Risiken)

---

## Risiken

🟡 **Kein Store-State für Suche/Sortierung/View-Modus.** Bewusste Abweichung
vom ursprünglichen Vorschlag: Die Personen-Liste wird komplett undpaginiert
geladen (`selectAll`), Suche/Sort/Gruppen-Filter/View-Modus sind reine
Darstellungs-Ableitungen ohne Server-Rundreise — anders als die Galerie-Filter
(die serverseitige Pagination steuern). Lokale Signals in `Personen` sind
daher der schlankere, konsistentere Weg. Nur die Gruppen-**Zuweisung**
(persistente Änderung) geht über den Store.

🟡 **`created_at` für Bestandspersonen ist NULL.** Sortierung „nach
Erstellungsdatum" muss NULL-Werte konsistent einsortieren (empfohlen: ans
Ende, unabhängig von Sortierrichtung) statt sie zufällig zu verteilen.

🟡 **Leichte Dateiüberschneidung mit P13 Phase 2/3.** Beide Pläne fassen
`persons.actions.ts` / `person.service.ts` an, aber unterschiedliche
Action-Namen — kein inhaltlicher Konflikt, nur beim Mergen der Diffs kurz
hinschauen.

🟡 **Clustering-Sicherheit bereits verifiziert (nicht mehr offen):**
`clustering/engine.py:162-179` reassigned ausschließlich Gesichter mit
`person_id == unknown_person_id`; `person_folders.py:263-270` verschiebt
keine bereits materialisierten Zuordnungen. Der Button auf der Personen-Seite
ruft nur den bestehenden, bereits sicheren Job auf — kein neues Risiko.

---

## Archiv-Footer

**Summary:** —
**Files touched:** —
**Commits:** —
**Deviations:** —
**Follow-ups:** —
