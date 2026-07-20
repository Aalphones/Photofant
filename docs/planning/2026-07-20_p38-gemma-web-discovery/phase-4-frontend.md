# Phase 4 — Frontend: Recherchieren-Button, Erklär-Dialog, Ergebnis-UI

**Komplexität:** standard (folgt dem „Ergänzen (KI)"-Muster aus P27 Phase 3 sehr eng) — die
Erstnutzung-Erklärung ist der einzige wirklich neue UI-Baustein (Idiotensicherheits-Gate).
**Voraussetzung:** Phase 3 abgeschlossen (Route + Guards funktionieren per curl/Postman).

## Kontext (lesen vor dem Start)
- `frontend/src/app/features/galerie/lightbox/lore-panel/lore-panel.ts` Zeile 150-234 —
  komplettes Muster für „KI-Ergänzung": Signale, Konstruktor-Subscribe, `requestUpdateSuggestion`.
  Die neue Discovery-Funktion kopiert diese Struktur, **ohne** den Annehmen/Ablehnen-Schritt
  (Discovery hat kein Proposal zum Bestätigen — sie hat schon geschrieben, wenn das
  Job-Ergebnis ankommt).
- `frontend/src/app/features/galerie/lightbox/lore-panel/lore-panel.html` Zeile 55-146 —
  Result-/Error-Rendering-Muster (Zeile 55-106) und der Button-Container `.lore-actions`
  (112-145), wo der neue Button dazukommt.
- `frontend/src/app/services/knowledge.service.ts` Zeile 100-131 — Methoden-Muster
  (`requestUpdateSuggestion`).
- `frontend/src/app/models/knowledge.model.ts` Zeile 79-99 (`LoreDto`, `DomainDto`),
  135-141 (`AiAutonomyDto`, `AI_AUTONOMY_MODES`).
- `frontend/src/app/models/job.model.ts` Zeile 4-5 (`JOB_KINDS`).
- `frontend/src/app/ui/icon/icon.ts` — verfügbare Icons; `search` (Zeile 16) für den neuen
  Button, kein neues SVG nötig.
- `frontend/src/app/features/wissen/wissen.ts` Zeile 20, 46 — Beispiel, wie `DomainDto.private`
  bereits an anderer Stelle im Projekt geprüft wird (`domains().some(d => d.private)`).

## Aufgabe 1 — Models
`models/job.model.ts`: `'knowledge_discovery'` zur `JOB_KINDS`-Liste hinzufügen (nach
`'interview'`, vor `'recommendation'`).

`models/knowledge.model.ts`:
```ts
export interface AiAutonomyDto {
  knowledge_import: AiAutonomyMode;
  knowledge_update: AiAutonomyMode;
  interview: AiAutonomyMode;
  discovery: AiAutonomyMode;  // nur 'off'/'auto' praktisch relevant, kein 'ask' (P38/ADR-031)
}

export interface DiscoveryRequest {
  entity_id: string;
}

export interface DiscoveryResponse {
  job_id: string;
}

export interface KnowledgeDiscoveryExplainability {
  model_id: string;
  capability: string;
  prompt_version: string;
  duration_ms: number;
  confidence: number | null;
  reason: string;
}

export interface KnowledgeDiscoveryResult {
  written_fields: string[];
  created_entities: { id: string; title: string; type: string }[];
  sources: string[];
  errors: string[];
  explainability: KnowledgeDiscoveryExplainability;
}
```

## Aufgabe 2 — Service
`services/knowledge.service.ts`, nach `acceptUpdateSuggestion` einfügen:
```ts
  // P38 — löst den KnowledgeDiscoveryJob aus (Websuche + Auto-Write, ADR-031). Anders als
  // requestUpdateSuggestion gibt es hier keinen Accept-Schritt: das Ergebnis im Job-Stream
  // beschreibt, was bereits geschrieben wurde.
  requestDiscovery(request: DiscoveryRequest): Observable<DiscoveryResponse> {
    return this.http.post<DiscoveryResponse>('/api/knowledge/ai/discovery', request);
  }
```

## Aufgabe 3 — Lore-Panel-Komponente
`lore-panel.ts` — neue Signale nach `updateAcceptPending` (Zeile 159):
```ts
  // ── Web-Discovery (P38) — „Recherchieren" ────────────────────────────────
  // Private Domänen werden zusätzlich zum Backend-Guard schon im UI ausgeblendet — dafür
  // einmalig die Domänen-Liste laden (dieselbe Quelle wie wissen.ts, hier aber lokal
  // gehalten statt über den Store, konsistent mit der self-contained-Konvention des Panels).
  protected readonly privateDomainNames = signal<Set<string>>(new Set());
  protected readonly discoveryAutonomy = signal<AiAutonomyDto | null>(null);
  protected readonly discoveryEntityId = signal<string | null>(null);
  protected readonly discoveryPending = signal(false);
  protected readonly discoveryResult = signal<KnowledgeDiscoveryResult | null>(null);
  protected readonly discoveryError = signal<string | null>(null);
  // Erstnutzung-Erklärung (Idiotensicherheits-Gate): einmal pro Browser, nicht pro Klick.
  protected readonly discoveryExplainerOpen = signal(false);
  private discoveryExplainerPendingEntityId: string | null = null;
  private static readonly DISCOVERY_EXPLAINER_SEEN_KEY = 'pf-discovery-explainer-seen';
```

Im Konstruktor, nach dem `getAiAutonomy()`-Subscribe (Zeile 164):
```ts
    this.knowledgeService.getAiAutonomy()
      .pipe(take(1), catchError(() => of(null)))
      .subscribe((autonomy: AiAutonomyDto | null): void => {
        this.updateAutonomy.set(autonomy);
        this.discoveryAutonomy.set(autonomy);
      });

    this.knowledgeService.listDomains()
      .pipe(take(1), catchError(() => of([])))
      .subscribe((domains: DomainDto[]): void => {
        this.privateDomainNames.set(new Set(domains.filter((d) => d.private).map((d) => d.name)));
      });
```
(`updateAutonomy` und `discoveryAutonomy` bleiben zwei getrennte Signale, obwohl beide aus
derselben Response kommen — spiegelt, dass es zwei unabhängige Funktionen mit eigenem
Autonomie-Schalter sind, nicht künstlich zusammengelegt.)

Im bestehenden `effect()`-Reset-Block (Zeile 169-180) ergänzen:
```ts
      this.discoveryEntityId.set(null);
      this.discoveryResult.set(null);
      this.discoveryError.set(null);
      this.discoveryPending.set(false);
```

Neue Methoden, nach `requestUpdateSuggestion` (nach Zeile 224):
```ts
  // `lore.entity.domain` ist der Domänen-Name (nicht die Domäne selbst) — Abgleich gegen
  // die einmalig geladene Menge privater Domänen-Namen.
  protected canRequestDiscoveryFor(lore: LoreDto): boolean {
    if (lore.entity == null) return false;
    return (
      this.canCorrectFor(lore) &&
      this.discoveryAutonomy()?.discovery === 'auto' &&
      !this.privateDomainNames().has(lore.entity.domain)
    );
  }

  protected onDiscoveryClick(entityId: string): void {
    if (localStorage.getItem(LorePanel.DISCOVERY_EXPLAINER_SEEN_KEY) == null) {
      this.discoveryExplainerPendingEntityId = entityId;
      this.discoveryExplainerOpen.set(true);
      return;
    }
    this.requestDiscovery(entityId);
  }

  protected confirmDiscoveryExplainer(): void {
    localStorage.setItem(LorePanel.DISCOVERY_EXPLAINER_SEEN_KEY, '1');
    this.discoveryExplainerOpen.set(false);
    const entityId = this.discoveryExplainerPendingEntityId;
    this.discoveryExplainerPendingEntityId = null;
    if (entityId != null) this.requestDiscovery(entityId);
  }

  protected cancelDiscoveryExplainer(): void {
    this.discoveryExplainerOpen.set(false);
    this.discoveryExplainerPendingEntityId = null;
  }

  private requestDiscovery(entityId: string): void {
    this.discoveryEntityId.set(entityId);
    this.discoveryResult.set(null);
    this.discoveryError.set(null);
    this.discoveryPending.set(true);
    this.knowledgeService.requestDiscovery({ entity_id: entityId })
      .pipe(
        switchMap((response: DiscoveryResponse): Observable<Job> =>
          this.jobsService.streamJobs().pipe(
            filter((job: Job): boolean =>
              job.id === response.job_id && (job.state === 'done' || job.state === 'error'),
            ),
            take(1),
          ),
        ),
      )
      .subscribe({
        next: (job: Job): void => {
          this.discoveryPending.set(false);
          if (job.state === 'error') {
            this.discoveryError.set(job.error ?? 'Recherche fehlgeschlagen');
            return;
          }
          if (job.result == null) {
            this.discoveryError.set('Recherche fehlgeschlagen');
            return;
          }
          this.discoveryResult.set(job.result as unknown as KnowledgeDiscoveryResult);
        },
        error: (): void => {
          this.discoveryPending.set(false);
          this.discoveryError.set('Recherche fehlgeschlagen');
        },
      });
  }

  protected dismissDiscoveryResult(): void {
    this.discoveryEntityId.set(null);
    this.discoveryResult.set(null);
    this.discoveryError.set(null);
  }
```
(`LorePanel` in `localStorage.getItem(LorePanel.DISCOVERY_EXPLAINER_SEEN_KEY)` durch den
tatsächlichen Klassennamen der Komponente ersetzen, falls er nicht `LorePanel` heißt — kurz
den `@Component`-Klassennamen oben in der Datei prüfen.)

## Aufgabe 4 — Template
`lore-panel.html`, im `.lore-actions`-Block (Zeile 134-144) nach dem „Ergänzen (KI)"-Button
ergänzen:
```html
            @if (canRequestDiscoveryFor(lore)) {
              <button
                class="lore-correct"
                type="button"
                (click)="onDiscoveryClick(ent.id)"
                [disabled]="discoveryPending()"
                title="Web-Recherche — schreibt automatisch, ohne Rückfrage"
              >
                <pf-icon name="search" [size]="11" />
                {{ discoveryPending() && discoveryEntityId() === ent.id ? 'Recherchiert…' : 'Recherchieren' }}
              </button>
            }
```

Owner-Hinweis für automatisch geschriebene Inhalte — im Bio-Block (um Zeile 108-111,
`@else { @if (bioFor(lore); as text) { ... } }`) ergänzen, direkt vor `<p class="lore-bio">`:
```html
          @if (ent.owner === 'web') {
            <p class="lore-web-hint">🌐 Automatisch per Web-Recherche ergänzt — noch nicht
              von dir geprüft.</p>
          }
```
(`.lore-web-hint` in `lore-panel.scss` mit denselben dezenten Stil-Werten wie die
bestehenden `.lore-suggestion__status`/`.lore-correction__error`-Klassen anlegen — kleine
Schrift, gedämpfte Farbe, keine neue Farbpalette erfinden.)

Ergebnis-/Fehler-Anzeige, direkt nach dem „Ergänzen (KI)"-Result-Block (nach Zeile 106,
noch innerhalb desselben `@if (canRequestUpdateFor...)`-umschließenden Bereichs — als
eigener, unabhängiger Block, da Discovery unabhängig von der Update-Suggestion läuft):
```html
    @if (discoveryEntityId() === ent.id) {
      <div class="lore-suggestion">
        @if (discoveryPending()) {
          <p class="lore-suggestion__status">Gemma recherchiert und schreibt automatisch…</p>
        } @else {
          @if (discoveryError(); as err) {
            <p class="lore-correction__error">{{ err }}</p>
          }
          @if (discoveryResult(); as result) {
            @if (result.written_fields.length > 0) {
              <p class="lore-suggestion__reason">Beschreibung ergänzt.</p>
            }
            @if (result.created_entities.length > 0) {
              <p class="lore-suggestion__reason">
                Neu angelegt: {{ result.created_entities.map(e => e.title).join(', ') }}
              </p>
            }
            @if (result.written_fields.length === 0 && result.created_entities.length === 0) {
              <p class="lore-suggestion__status">Nichts Neues gefunden.</p>
            }
            @if (result.errors.length > 0) {
              <p class="lore-web-hint">{{ result.errors.join(' · ') }}</p>
            }
          }
          <div class="lore-correction__actions">
            <button class="lore-correction__cancel" type="button" (click)="dismissDiscoveryResult()">
              Schließen
            </button>
          </div>
        }
      </div>
    }
```

**Genaue Platzierung im bestehenden Template selbst festlegen** (Datei vor dem Edit einmal
komplett lesen — der obige Block braucht denselben `@for`-Scope wie `ent`/`lore`, wie der
existierende Update-Suggestion-Block; wo genau innerhalb der `panel-sec`-Struktur er sitzt,
hängt vom exakten Verschachtelungs-Stand beim Umsetzen ab, nicht am 2026-07-20-Stand
festnageln).

## Aufgabe 5 — Erstnutzung-Erklär-Dialog (Idiotensicherheits-Gate)
Kein neuer eigener Dialog-Component nötig — ein einfacher Overlay-Block direkt in
`lore-panel.html` (analog zu anderen einfachen Confirm-Overlays im Projekt, z.B.
`rerun-dialog` als Strukturvorbild grob anschauen, kein 1:1-Kopieren nötig, das hier ist
deutlich simpler):
```html
@if (discoveryExplainerOpen()) {
  <div class="discovery-explainer-scrim">
    <div class="discovery-explainer">
      <h3>Web-Recherche</h3>
      <p>
        Diese Aktion sucht im Web nach dieser Person/Sache und schreibt Ergebnisse
        <strong>direkt und ohne weitere Rückfrage</strong> in die Wissensbasis — anders als
        die anderen KI-Vorschläge hier. Du kannst jede Änderung danach im Verlauf
        ("Warum geändert?") einsehen und wie jeden anderen Wert korrigieren.
      </p>
      <div class="lore-correction__actions">
        <button class="lore-correction__save" type="button" (click)="confirmDiscoveryExplainer()">
          Verstanden, weiter
        </button>
        <button class="lore-correction__cancel" type="button" (click)="cancelDiscoveryExplainer()">
          Abbrechen
        </button>
      </div>
    </div>
  </div>
}
```
Erscheint **einmal pro Browser** (localStorage-Flag, Aufgabe 3) — danach läuft „Recherchieren"
direkt durch, wie vom User entschieden (Opt-in ist die einmalige Erklärung + der bewusste
Klick pro Entity, nicht ein Dialog bei jeder Nutzung).

## Aufgabe 6 — P27-README amendieren (nicht neu schreiben, zwei Zeilen ergänzen)
`docs/planning/2026-07-01_p27-gemma-integration/README.md`:
- Bei der AK-Zeile „Offline-Garantie gewahrt: …" ergänzen: „*(Ausnahme ab P38: die
  Web-Discovery-Capability macht bei explizitem User-Trigger echte Netzwerkzugriffe —
  ADR-031. Alle anderen P27-Funktionen bleiben strikt offline.)*"
- Beim Scope-„Draußen"-Punkt „Discovery → Phase 8" ergänzen: „*(Web-Recherche für öffentliche
  Entitäten ist vorgezogen als P38 — vollautomatische Hintergrund-Discovery ohne User-Trigger
  bleibt weiterhin Phase 8.)*"

## AK dieser Phase
- [ ] Bei `ai.autonomy.discovery == "off"` (Default) ist der „Recherchieren"-Button nirgends
      sichtbar — auch nicht auf einer öffentlichen Entity.
- [ ] Nach Setzen auf `"auto"`: Button sichtbar auf öffentlichen Entities, **nicht** sichtbar
      auf privaten (Person/Pet aus `private.yaml`).
- [ ] Erster Klick im Browser zeigt den Erklär-Dialog; „Verstanden, weiter" löst die Recherche
      aus; jeder folgende Klick (gleicher Browser) läuft direkt durch.
- [ ] Ergebnis-Panel zeigt nach Abschluss sichtbar, was geschrieben/angelegt wurde; ein Fehler
      im Job zeigt eine verständliche Meldung, keinen leeren/kaputten Zustand.
- [ ] Owner-Hinweis „🌐 Automatisch ergänzt" erscheint an einer Entity, deren Body zuletzt via
      Discovery geschrieben wurde.

## Doc-Updates
- [ ] `docs/code-map.md` — „KI-Layer / Gemma"-Zeile um die neuen Frontend-Dateien/-Signale
      ergänzen (Muster wie die bestehenden Phase-2/3/4-Einträge).
- [ ] `docs/glossary.md` prüfen — falls „Owner"/„web" dort noch nicht als Begriff auftaucht,
      einen kurzen Eintrag ergänzen (bestehender Begriff, jetzt erstmals sichtbar genutzt).

## Report-Back
