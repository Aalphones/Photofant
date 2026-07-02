# Phase 4 — Frontend UI: Toolbar, Grid, Karte, Clustering-Button

**Tier:** standard
**Status:** complete
**Voraussetzung:** Phase 2 abgeschlossen (`group_name`/`created_at` im Store)

---

## Kontext (vorher lesen)

- `frontend/src/app/features/personen/personen.ts` / `.html` / `.scss`
- `frontend/src/app/features/personen/person-card/person-card.ts` / `.html` / `.scss`
- `frontend/src/app/features/galerie/grid/grid.html` / `.scss` — Vorlage für Section-Header-Stil (`grid__month-head`)
- `frontend/src/app/features/galerie/sub-toolbar/sub-toolbar.ts` — Vorlage für Sortier-Zyklus (`cycleSortKey`) und Filter-Chips
- `frontend/src/app/features/einstellungen/backup-wartung/backup-wartung.html` (Zeile 6-31) — bestehender Clustering-Button, 1:1-Wiederverwendung der Actions
- `frontend/src/app/ui/icon/icon.ts` — verfügbare Icons: `search`, `sort`, `filter`, `layers`, `face`, `album`, `user`

**Architektur-Entscheidung (siehe README-Risiken):** Suche, Sortierung,
Gruppen-Filter und View-Modus leben als **lokale Signals** in `Personen` —
kein Store-Roundtrip nötig, da die Personen-Liste komplett unpaginiert
geladen ist. Section-Header (Gruppierung) erscheinen **nur**, wenn
`sortKey() === 'group'`; bei `created`/`name` wird flach sortiert gerendert.

---

## Abnahme-Kriterien

- [x] Schnellsuche filtert live nach `name` (case-insensitive, `is_unknown`-Personen bleiben durchsuchbar über „Unbekannt")
- [x] Sortier-Icon zykelt Gruppe → Erstellungsdatum (neueste zuerst) → Name (A-Z), Label zeigt aktuellen Modus
- [x] Bei Sortierung „Gruppe": Section-Header pro Gruppe (Stil wie `grid__month-head`), „Ohne Gruppe" als letzter Bucket
- [x] Gruppen-Filter-Chips: Mehrfachauswahl, nur Gruppen zeigen, die tatsächlich vergeben sind
- [x] View-Toggle: Einzelfoto / 4er-Grid / Gesichtsausschnitt (aktuelles Verhalten), Auswahl bleibt für die Session erhalten
- [x] Alphabet-Leiste springt zur ersten Person mit passendem Anfangsbuchstaben
- [x] Gruppen-Zuweisung an der Personen-Karte (Freitext, analog Rename-Inline-Edit)
- [x] „Clustering starten"-Button in der Personen-Toolbar, nutzt bestehenden `isClustering`-State

---

## Checkliste

### personen.ts — lokaler Filter-/Sortier-/View-State

- [x] Neue Typen (lokal in der Datei oder `personen.model.ts`, falls es das schon gibt):
  ```typescript
  type PersonSortKey = 'group' | 'created' | 'name';
  type PersonViewMode = 'single' | 'grid4' | 'face';
  ```
- [x] Signals:
  ```typescript
  protected readonly searchQuery = signal('');
  protected readonly sortKey     = signal<PersonSortKey>('group');
  protected readonly groupFilter = signal<Set<string>>(new Set());
  protected readonly viewMode    = signal<PersonViewMode>('face');
  ```
- [x] `availableGroups` computed — alle vorkommenden `group_name`-Werte, sortiert:
  ```typescript
  protected readonly availableGroups = computed((): string[] => {
    const names = new Set<string>();
    for (const person of this.persons()) {
      if (person.group_name) { names.add(person.group_name); }
    }
    return [...names].sort((a, b) => a.localeCompare(b));
  });
  ```
- [x] `filteredPersons` computed — Suche + Gruppen-Filter anwenden (vor Sortierung):
  ```typescript
  protected readonly filteredPersons = computed((): PersonDto[] => {
    const query = this.searchQuery().trim().toLowerCase();
    const groups = this.groupFilter();
    return this.persons().filter((person: PersonDto) => {
      if (query) {
        const label = (person.is_unknown ? 'unbekannt' : (person.name ?? '')).toLowerCase();
        if (!label.includes(query)) { return false; }
      }
      if (groups.size > 0) {
        if (!person.group_name || !groups.has(person.group_name)) { return false; }
      }
      return true;
    });
  });
  ```
- [x] `sortedPersons` computed — nach `sortKey()`:
  ```typescript
  protected readonly sortedPersons = computed((): PersonDto[] => {
    const list = [...this.filteredPersons()];
    if (this.sortKey() === 'name') {
      return list.sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));
    }
    if (this.sortKey() === 'created') {
      return list.sort((a, b) => {
        const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
        const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
        return bTime - aTime; // neueste zuerst, NULL (=0) landet am Ende
      });
    }
    return list; // 'group' — Gruppierung übernimmt die Sortierung in personGroups()
  });
  ```
- [x] `personGroups` computed — nur relevant für `sortKey() === 'group'`, sonst leer:
  ```typescript
  protected readonly personGroups = computed((): { label: string; persons: PersonDto[] }[] => {
    if (this.sortKey() !== 'group') { return []; }
    const buckets = new Map<string, PersonDto[]>();
    for (const person of this.sortedPersons()) {
      const key = person.group_name ?? 'Ohne Gruppe';
      const bucket = buckets.get(key) ?? [];
      bucket.push(person);
      buckets.set(key, bucket);
    }
    const entries = [...buckets.entries()].sort(([a], [b]) => {
      if (a === 'Ohne Gruppe') { return 1; }
      if (b === 'Ohne Gruppe') { return -1; }
      return a.localeCompare(b);
    });
    return entries.map(([label, persons]) => ({ label, persons }));
  });
  ```
- [x] `cycleSortKey()`:
  ```typescript
  private readonly SORT_CYCLE: PersonSortKey[] = ['group', 'created', 'name'];

  protected cycleSortKey(): void {
    const currentIndex = this.SORT_CYCLE.indexOf(this.sortKey());
    this.sortKey.set(this.SORT_CYCLE[(currentIndex + 1) % this.SORT_CYCLE.length]);
  }

  protected sortLabel(): string {
    const labels: Record<PersonSortKey, string> = {
      group: 'Gruppe', created: 'Erstellungsdatum', name: 'Name',
    };
    return labels[this.sortKey()];
  }
  ```
- [x] `toggleGroupFilter(groupName: string)`:
  ```typescript
  protected toggleGroupFilter(groupName: string): void {
    const next = new Set(this.groupFilter());
    if (next.has(groupName)) { next.delete(groupName); } else { next.add(groupName); }
    this.groupFilter.set(next);
  }
  ```
- [x] `setViewMode(mode: PersonViewMode)` + `onSetGroup(event: { id: number; groupName: string })`:
  ```typescript
  protected setViewMode(mode: PersonViewMode): void {
    this.viewMode.set(mode);
  }

  protected onSetGroup(event: { id: number; groupName: string }): void {
    this.store.dispatch(personsActions.setPersonGroup({ id: event.id, groupName: event.groupName || null }));
  }

  protected readonly isClustering = this.store.selectSignal(personsSelectors.selectIsClustering);

  protected triggerClustering(): void {
    this.store.dispatch(personsActions.triggerClustering());
  }
  ```

### group-color.util.ts (neu, co-located in `features/personen/`)

- [x] Deterministische Hash → HSL-Farbe (keine externe Lib nötig):
  ```typescript
  export function groupColor(groupName: string): string {
    let hash = 0;
    for (let index = 0; index < groupName.length; index++) {
      hash = (hash << 5) - hash + groupName.charCodeAt(index);
      hash |= 0;
    }
    const hue = Math.abs(hash) % 360;
    return `hsl(${hue}, 55%, 55%)`;
  }
  ```

### personen.html — Toolbar erweitern

- [x] Schnellsuche-Input (debounced über `signal` reicht, kein RxJS nötig bei clientseitigem Filter):
  ```html
  <div class="personen__search">
    <pf-icon name="search" [size]="14" />
    <input
      type="text"
      placeholder="Personen durchsuchen…"
      [value]="searchQuery()"
      (input)="searchQuery.set($any($event.target).value)"
    />
  </div>
  ```
- [x] Sortier-Button:
  ```html
  <button class="personen__action-btn" (click)="cycleSortKey()" [title]="'Sortiert nach: ' + sortLabel()">
    <pf-icon name="sort" [size]="14" />
    {{ sortLabel() }}
  </button>
  ```
- [x] Gruppen-Filter-Chips (nur wenn `availableGroups().length > 0`):
  ```html
  @if (availableGroups().length > 0) {
    <div class="personen__group-chips">
      @for (group of availableGroups(); track group) {
        <button
          class="personen__group-chip"
          [class.personen__group-chip--active]="groupFilter().has(group)"
          [style.--chip-color]="groupColor(group)"
          (click)="toggleGroupFilter(group)"
        >{{ group }}</button>
      }
    </div>
  }
  ```
- [x] View-Toggle (3 Icons):
  ```html
  <div class="personen__view-toggle">
    <button [class.active]="viewMode() === 'single'" (click)="setViewMode('single')" title="Einzelfoto"><pf-icon name="album" [size]="14" /></button>
    <button [class.active]="viewMode() === 'grid4'" (click)="setViewMode('grid4')" title="4er-Grid"><pf-icon name="layers" [size]="14" /></button>
    <button [class.active]="viewMode() === 'face'" (click)="setViewMode('face')" title="Gesichtsausschnitt"><pf-icon name="face" [size]="14" /></button>
  </div>
  ```
- [x] Clustering-Button (analog `backup-wartung.html` Zeile 18-28, kompakter):
  ```html
  <button class="personen__action-btn" [disabled]="isClustering()" (click)="triggerClustering()" title="Gruppiert alle unbekannten Gesichter neu">
    @if (isClustering()) {
      <span class="spinner"></span> Läuft…
    } @else {
      <pf-icon name="scan" [size]="14" /> Clustering starten
    }
  </button>
  ```

### personen.html — Grid mit Section-Headern

- [x] Bei `sortKey() === 'group'`: `personGroups()` mit Headern rendern (Stil analog `grid__month-head`)
- [x] Sonst: `sortedPersons()` flach rendern
- [x] Alphabet-Leiste als eigene Komponente einbinden (siehe unten), `personen` an `sortedPersons()` weiterreichen

### alphabet-rail (neu, `features/personen/alphabet-rail/`)

- [x] `ng generate component features/personen/alphabet-rail --skip-tests`
- [x] Input: `persons = input<PersonDto[]>([])`, Output: `jump = output<number>()` (Personen-ID der ersten Person mit dem Buchstaben)
- [x] Berechnet vorhandene Anfangsbuchstaben aus `persons()`, disabled für fehlende Buchstaben
- [x] `Personen`-Komponente: `scrollIntoView` auf die passende `pf-person-card` (via `id`-Attribut oder `ViewChildren` + `find`)

### person-card.ts / .html — Gruppen-Zuweisung + View-Modi

- [x] Neuer Output: `setGroup = output<{ id: number; groupName: string }>()`
- [x] Long-Press-Menü um „Gruppe zuweisen" erweitern (analog `onRenameClick`/`startEdit`-Pattern), eigenes Signal `isEditingGroup`
- [x] Neuer Input: `viewMode = input<'single' | 'grid4' | 'face'>('face')`
- [x] Template: je nach `viewMode()` unterschiedliche Bild-Darstellung:
  - `face`: aktuelles Verhalten (Portrait-Face-Crop) — unverändert
  - `single`: größtes/erstes reguläres Foto der Person (neuer Service-Call oder vorhandenes Feld nutzen — 🟡 prüfen ob `PersonFaceDto`/Asset-Thumbnail dafür reicht oder ein neues DTO-Feld nötig ist)
  - `grid4`: 2×2-Ausschnitt aus bis zu 4 Fotos/Gesichtern der Person
  - 🟡 **Scope-Check:** falls `single`/`grid4` ein neues Backend-Feld brauchen (z.B. `recent_photo_urls: string[]`), das in FINDINGS.md festhalten und ggf. als eigene Mini-Iteration nachziehen statt Phase 3 zu sprengen — Kernanforderung (Suche/Gruppe/Sortierung) hat Vorrang vor der Bild-Vielfalt der View-Modi.
- [x] `person-card.scss`: Gruppen-Badge (nutzt `groupColor()`) klein am Kartenrand, nicht aufdringlich

---

## Doc-Updates

- [x] `docs/code-map.md` — `alphabet-rail`, `group-color.util.ts` unter `features/personen/` ergänzen
- [x] Keine neuen Settings-Keys
