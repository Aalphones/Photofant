import { ChangeDetectionStrategy, Component, computed, effect, inject } from '@angular/core';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import { knowledgeActions, knowledgeSelectors } from '@photofant/store';
import type { AiAutonomyDto, AiAutonomyMode } from '@photofant/models';

interface AutonomyOption {
  value: AiAutonomyMode;
  label: string;
}

// off/ask/auto — die drei Funktionen mit Bestätigungs-Zwischenschritt (P27)
const THREE_WAY_OPTIONS: AutonomyOption[] = [
  { value: 'off', label: 'Aus' },
  { value: 'ask', label: 'Fragen' },
  { value: 'auto', label: 'Automatisch' },
];

// discovery kennt bewusst kein "ask" — die Bestätigung sitzt im Wizard, nicht hier (ADR-031)
const TWO_WAY_OPTIONS: AutonomyOption[] = [
  { value: 'off', label: 'Aus' },
  { value: 'auto', label: 'Automatisch' },
];

@Component({
  selector: 'pf-einstellungen-ki',
  imports: [Icon],
  templateUrl: './ki.html',
  styleUrl: './ki.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KiSection {
  private readonly store = inject(Store);

  readonly autonomy = this.store.selectSignal(knowledgeSelectors.selectAiAutonomy);
  readonly isSaving = this.store.selectSignal(knowledgeSelectors.selectAiAutonomySaving);
  readonly error = this.store.selectSignal(knowledgeSelectors.selectAiAutonomySaveError);

  readonly threeWayOptions = THREE_WAY_OPTIONS;
  readonly twoWayOptions = TWO_WAY_OPTIONS;

  readonly knowledgeImport = computed((): AiAutonomyMode => this.autonomy()?.knowledge_import ?? 'off');
  readonly knowledgeUpdate = computed((): AiAutonomyMode => this.autonomy()?.knowledge_update ?? 'off');
  readonly interview = computed((): AiAutonomyMode => this.autonomy()?.interview ?? 'off');
  readonly discovery = computed((): AiAutonomyMode => this.autonomy()?.discovery ?? 'off');

  constructor() {
    effect(() => {
      this.store.dispatch(knowledgeActions.loadAiAutonomy());
    });
  }

  setKnowledgeImport(value: AiAutonomyMode): void {
    this.patch({ knowledge_import: value });
  }

  setKnowledgeUpdate(value: AiAutonomyMode): void {
    this.patch({ knowledge_update: value });
  }

  setInterview(value: AiAutonomyMode): void {
    this.patch({ interview: value });
  }

  setDiscovery(value: AiAutonomyMode): void {
    this.patch({ discovery: value });
  }

  private patch(patch: Partial<AiAutonomyDto>): void {
    this.store.dispatch(knowledgeActions.updateAiAutonomy({ patch }));
  }
}
