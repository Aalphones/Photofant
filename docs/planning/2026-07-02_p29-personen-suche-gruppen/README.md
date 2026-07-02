# P29 — Personen durchsuchen, filtern, gruppieren

**Status:** pending

Personen-Tab wird bei vielen Personen unübersichtlich. Freitext-Gruppen (z.B.
„Familie", „Freunde"), Schnellsuche, Sortierung und ein View-Toggle
(Einzelfoto / 4er-Grid / Gesichtsausschnitt) machen ihn wieder schnell
erfassbar. Zusätzlich wandert der bestehende Clustering-Trigger aus den
Einstellungen auch auf die Personen-Seite (bestehende Store-Actions, reines
UI-Wiring).

Der Clustering-Lauf selbst wird dabei erweitert: bisher bildet er aus allen
noch unbekannten Gesichtern per HDBSCAN ausschließlich neue Personen-Buckets
und prüft nie, ob eine passende Person inzwischen schon existiert (z.B. weil
sie erst nach dem letzten Lauf angelegt wurde). Neu: erst pro Gesicht gegen
bestehende Personen matchen (gleiche Schwellwerte wie beim Incremental-Match
nach dem Import), erst der Rest wird wie bisher neu geclustert.

---

## Overview

| Phase | Thema | Tier | Status |
|---|---|---|---|
| 1 | Backend — Clustering: erst gegen bestehende Personen matchen, dann Rest clustern | standard | complete |
| 2 | Backend — Gruppenfeld + Erstellungsdatum | standard | complete |
| 3 | Frontend Store — Persistenz für Gruppen-Zuweisung | standard | complete |
| 4 | Frontend UI — Toolbar, Grid, Karte, Clustering-Button | standard | pending |
| 5 | Politur — Zusatz-Sortierungen, Empty-States, Perf-Check | standard | pending |
| 6 | Person löschen — Ordner + DB-Eintrag entfernen, Fotos wandern nach „Unbekannt" | standard | pending |

---

## Kontrakt (Cross-Modul-Ankerpunkt)

### Backend — Clustering-Algorithmus (Phase 1 — clustering/engine.py)

Neuer Ablauf in `run_initial_clustering`:

1. Für jedes Gesicht, das noch bei „Unbekannt" hängt (und nicht `fixed_person`
   ist): erst `match_face_incremental()` gegen alle **bestehenden**
   (nicht-unknown) Personen laufen lassen — dieselbe Funktion, dieselben
   Settings-Schwellwerte (`face_auto_threshold`, `face_review_threshold`) wie
   beim Incremental-Match direkt nach dem Import.
   - `auto`-Band → Gesicht wird sofort der bestehenden Person zugewiesen,
     Ordner materialisiert (wie in `clustering_job.run_incremental_match`,
     Zeilen 64-78 — 1:1 wiederverwendet).
   - `review`-Band → `ReviewItem` (`type="face_suggestion"`) angelegt, Gesicht
     bleibt vorerst bei „Unbekannt", landet in der bestehenden Review-Queue
     (Zeilen 80-108 — 1:1 wiederverwendet, keine neue UI nötig).
   - Kein Match (`unknown`-Band) → Gesicht bleibt Kandidat für HDBSCAN.
2. Erst der verbleibende Rest (Gesichter ohne Match) durchläuft wie bisher
   HDBSCAN → neue Personen-Buckets.

Kein neuer Matching-Code — nur eine neue Aufrufreihenfolge im Batch-Lauf, die
bestehende Bausteine (`match_face_incremental`, Review-Queue-Logik) vor das
HDBSCAN-Clustering schaltet.

### Backend (Phase 2 — models.py + persons.py)

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

### Frontend — PersonDto (Phase 3)

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

### Frontend — neue NgRx-Action (Phase 3)

```typescript
// persons.actions.ts — neu
'Set Person Group':         props<{ id: number; groupName: string | null }>()
'Set Person Group Success': props<{ person: PersonDto }>()
'Set Person Group Failure': props<{ error: string }>()
```
Reine Persistenz-Aktion — Suche/Sortierung/View-Modus sind **kein** Store-State
(siehe Risiken unten), sondern lokale Signals in `Personen`.

### Frontend — Clustering-Button (Phase 4)

Wiederverwendet **1:1** bestehende Infrastruktur, keine neuen Actions:
```typescript
this.store.dispatch(personsActions.triggerClustering());
this.store.selectSignal(personsSelectors.selectIsClustering);
```

### Backend + Frontend — Person löschen (Phase 6)

```python
# api/persons.py
DELETE /persons/{person_id} → DeleteResultDto { faces_moved: int, instances_moved: int }
# 404 unbekannte Person-ID, 400 wenn is_unknown (Unbekannt-Person selbst nicht löschbar)
```
`media/person_folders.py` bekommt `delete_person()` — analog `merge_persons()`, aber Ziel ist
immer `_unknown`, ohne Namensübernahme, mit zurückgesetztem `fixed_person` (die Fotos müssen
nach dem Löschen wieder für Clustering/Incremental-Match verfügbar sein). Danach: Person-Row
weg, Ordner weg, Fotos/Edits/Faces liegen unversehrt in `_unknown`.

```typescript
// persons.actions.ts — neu (Ergebnis-Typ: bestehendes MergeResult wiederverwendet)
'Delete Person':         props<{ id: number }>()
'Delete Person Success': props<{ result: MergeResult }>()
'Delete Person Failure': props<{ error: string }>()
```
Nur über einen dedizierten Bestätigungsdialog (`delete-person-dialog`, neu) erreichbar, der
in Klartext sagt: Fotos werden **nicht** gelöscht, sondern wandern nach „Unbekannt" — nur die
Person und ihr Ordner sind danach weg.

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
- [ ] Clustering-Lauf matcht unbekannte Gesichter zuerst gegen bestehende Personen: über `face_auto_threshold` → direkt zugewiesen (Ordner materialisiert), zwischen `face_review_threshold` und `face_auto_threshold` → Vorschlag in der Review-Queue, darunter → wie bisher Kandidat für HDBSCAN
- [ ] Ein Gesicht, das seit dem letzten Clustering-Lauf durch eine neu angelegte Person passend würde, wird beim nächsten Lauf erkannt (auto- oder review-Fall, nicht mehr stumm neu geclustert)
- [ ] Person löschen entfernt Ordner + DB-Eintrag vollständig, Fotos/Edits/Faces landen unversehrt in „Unbekannt", „Unbekannt" selbst ist nicht löschbar
- [ ] Smart-Album-Trigger überleben Löschen (entfernt) und Zusammenführen (auf Zielperson umgebogen) einer Person, statt tot ins Leere zu zeigen

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
ruft nur den bestehenden, bereits sicheren Job auf — kein neues Risiko. Gilt
unverändert für den erweiterten Ablauf: die neue Matching-Vorstufe rührt
ebenfalls nur an Gesichtern mit `person_id == unknown_person_id`.

🟡 **Performance der Matching-Vorstufe (Phase 1).** Statt eines einzigen
HDBSCAN-Batch-Laufs gibt es jetzt zusätzlich einen `search_disjoint_persons`-
Call pro noch-unbekanntem Gesicht. Bei sehr vielen Unbekannten (mehrere
Tausend) ggf. spürbar langsamer als bisher — gehört in den ohnehin geplanten
Perf-Check (Phase 5).

🟡 **Review-Vorschläge landen ohne neue UI in der bestehenden Queue.** Phase 1
erzeugt `ReviewItem`s vom Typ `face_suggestion` — dieselbe Queue, die auch der
Incremental-Match nach Import befüllt. Kein zusätzlicher UI-Teil in P29 nötig,
aber Abnahme sollte einmal die bestehende Review-Ansicht nach einem
Clustering-Lauf gegenprüfen.

🟡 **Person löschen weicht bewusst von `merge_persons` ab: `fixed_person` wird
zurückgesetzt.** Bei einem normalen Merge bleibt `fixed_person` auf dem
verschobenen Instance-Eintrag unangetastet (Ziel ist ja weiterhin eine echte
Person). Beim Löschen landen die Fotos aber wieder im freien „Unbekannt"-Pool
— bliebe `fixed_person=True` stehen, würden genau diese Fotos vom nächsten
Clustering/Incremental-Match für immer übersprungen (`can_move_unknown`-Gate
in `person_folders.py`). Phase 6 setzt es deshalb explizit auf `False`.

🟡 **`SmartTrigger.person_id` würde ohne Gegenmaßnahme nach Löschen oder Merge
ins Leere zeigen — Phase 6 fixt beide Fälle.** Ein Smart-Album-Trigger vom Typ
„person" referenziert die Person per Fremdschlüssel ohne `ON DELETE`-Regel;
SQLite erzwingt Fremdschlüssel in diesem Projekt nicht. Ein gemeinsamer Helper
(`_resolve_person_smart_triggers`) räumt das für beide betroffenen Funktionen
auf: `delete_person()` löscht den Trigger (keine Nachfolge-Person vorhanden),
`merge_persons()` biegt ihn stattdessen auf die Zielperson um (die Fotos leben
dort ja weiter). Für Löschen reevaluiert die Route danach explizit die
betroffenen Assets; für Merge übernimmt das der bereits bestehende
Reevaluate-Call in `merge_persons_endpoint`.

---

## Archiv-Footer

**Summary:** —
**Files touched:** —
**Commits:** —
**Deviations:** —
**Follow-ups:** —
