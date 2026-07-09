import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, combineLatest, map, of, startWith, switchMap, type Observable } from 'rxjs';
import { KnowledgeService } from '@photofant/services';
import type { EntityRefDto, LoreDto, MediaRefDto, ResolvedRelationshipDto } from '@photofant/models';
import { Icon } from '@photofant/ui';

type LoreStatus = 'loading' | 'ready' | 'empty';

interface LoreState {
  status: LoreStatus;
  lore: LoreDto | null;
}

// Lore-Panel (P25): zeigt das gebündelte Wissen zum Bild/zur Person rechts in der Lightbox.
// Domänen-agnostisch gehaltene 5-Sektionen-Sicht (Kurzbio · Beziehungen · Franchises ·
// Eigene Bilder · Quellen) — „Rollen"/„Verwandte Entitäten" aus Dok 050 §5 fallen bewusst
// weg, ihre Info steckt in „Beziehungen" (keine Kopplung an domänenspezifische Typ-Strings).
// Dockt als weitere Panel-Sektion an P15s Lightbox-Panel an (kein zweiter Container).
@Component({
  selector: 'pf-lore-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './lore-panel.html',
  styleUrl: './lore-panel.scss',
})
export class LorePanel {
  private readonly knowledgeService = inject(KnowledgeService);

  readonly assetId = input<number | null>(null);
  readonly personId = input<number | null>(null);
  // Ob Wissen hier überhaupt sinnvoll wäre (Bild zeigt Personen) — steuert, ob der
  // „Noch kein Wissen — anlegen"-Zustand erscheint oder das Panel still ausgeblendet bleibt.
  readonly hasPersonContext = input(false);

  readonly entitySelected = output<EntityRefDto>();
  readonly createRequested = output<void>();

  // Lazy: lädt erst, wenn eine der ids gesetzt ist (Lightbox offen). catchError degradiert
  // still zum Leer-Zustand statt das Signal für den Rest der Session zu vergiften.
  private readonly state = toSignal(
    combineLatest([toObservable(this.assetId), toObservable(this.personId)]).pipe(
      switchMap(([assetId, personId]: [number | null, number | null]): Observable<LoreState> => {
        if (assetId == null && personId == null) {
          return of({ status: 'empty', lore: null });
        }
        return this.knowledgeService
          .getLore({ assetId, personId })
          .pipe(
            map((lore: LoreDto): LoreState => ({
              status: lore.entity != null ? 'ready' : 'empty',
              lore,
            })),
            startWith({ status: 'loading', lore: null } as LoreState),
            catchError((error: unknown): Observable<LoreState> => {
              console.error('[LorePanel] Lore konnte nicht geladen werden:', error);
              return of({ status: 'empty', lore: null });
            }),
          );
      }),
    ),
    { initialValue: { status: 'loading', lore: null } as LoreState },
  );

  protected readonly status = computed((): LoreStatus => this.state().status);
  protected readonly entity = computed(() => this.state().lore?.entity ?? null);

  protected readonly bio = computed((): string | null => {
    const body = this.entity()?.body?.trim();
    return body ? body : null;
  });

  // Beziehungen ohne die Franchise-Ziele — die stehen in ihrer eigenen Sektion. Dedup
  // domänen-agnostisch über die Franchise-ids statt über den Typ-String "Franchise"
  // (P25 Phase-1-Finding: franchises[] enthält Ziele zusätzlich zu relationships[]).
  protected readonly relationships = computed((): ResolvedRelationshipDto[] => {
    const lore = this.state().lore;
    if (lore == null) {
      return [];
    }
    const franchiseIds = new Set(lore.franchises.map((ref: EntityRefDto) => ref.id));
    return lore.relationships.filter(
      (relationship: ResolvedRelationshipDto) => !franchiseIds.has(relationship.target.id),
    );
  });

  protected readonly franchises = computed((): EntityRefDto[] => this.state().lore?.franchises ?? []);
  protected readonly relatedMedia = computed((): MediaRefDto[] => this.state().lore?.related_media ?? []);
  protected readonly sources = computed((): string[] => this.state().lore?.sources ?? []);

  protected readonly showEmptyState = computed((): boolean =>
    this.status() === 'empty' && this.hasPersonContext(),
  );

  // Ein Ziel ist nur navigierbar, wenn es eine aufgelöste Entity hat; unbekannte Ziele
  // kommen mit leerem Typ zurück (P25 Phase-1-Finding) — dann kein Navigationsziel.
  protected isNavigable(ref: EntityRefDto): boolean {
    return ref.type !== '';
  }

  protected selectEntity(ref: EntityRefDto): void {
    if (this.isNavigable(ref)) {
      this.entitySelected.emit(ref);
    }
  }

  protected requestCreate(): void {
    this.createRequested.emit();
  }

  protected relationTypeLabel(type: string): string {
    return type.replaceAll('_', ' ');
  }

  protected isUrl(source: string): boolean {
    return source.startsWith('http://') || source.startsWith('https://');
  }

  protected sourceLabel(source: string): string {
    try {
      return new URL(source).hostname.replace(/^www\./, '');
    } catch {
      return source;
    }
  }
}
