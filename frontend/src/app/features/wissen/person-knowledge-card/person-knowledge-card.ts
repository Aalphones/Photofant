import { ChangeDetectionStrategy, Component, computed, inject, input, output } from '@angular/core';
import type { PersonDto } from '@photofant/models';
import { PersonService } from '@photofant/services';
import { CompletenessRing, Icon } from '@photofant/ui';

// P38 Phase 5 — eine Karte im Personen-Grid der Wissen-Übersicht.
@Component({
  selector: 'pf-person-knowledge-card',
  imports: [CompletenessRing, Icon],
  templateUrl: './person-knowledge-card.html',
  styleUrl: './person-knowledge-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PersonKnowledgeCard {
  private readonly personService = inject(PersonService);

  readonly person = input.required<PersonDto>();
  // EntityRefDto (person().linked_entity) trägt keine Domäne — wissen.ts löst sie über
  // die vollständige Entity-Liste auf (entityDomainById) und reicht sie hier durch.
  readonly domain = input<string | null>(null);

  readonly openDetail = output<number>();

  protected readonly displayName = computed((): string => this.person().name ?? 'Unbenannt');

  protected readonly avatarUrl = computed((): string | null => {
    const faceId = this.person().portrait_face_id;
    return faceId != null ? this.personService.portraitUrl(faceId) : null;
  });

  protected readonly ringValue = computed((): number => this.person().linked_entity?.completeness ?? 0);

  protected readonly percent = computed((): number => Math.round(this.ringValue() * 100));

  protected onOpen(): void {
    this.openDetail.emit(this.person().id);
  }
}
