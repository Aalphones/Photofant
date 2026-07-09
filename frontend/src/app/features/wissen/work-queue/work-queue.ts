import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import type { TaskDto, TaskKind } from '@photofant/models';
import { Icon } from '../../../ui/icon/icon';

const KIND_LABELS: Record<TaskKind, string> = {
  new_person: 'Neue Person erkannt',
  missing_entity: 'Fehlende Entity',
  confirm_relationship: 'Beziehung bestätigen',
  review_recommendation: 'Empfehlung prüfen',
  incomplete_entity: 'Entity noch ohne Inhalt',
};

@Component({
  selector: 'pf-work-queue',
  imports: [Icon],
  templateUrl: './work-queue.html',
  styleUrl: './work-queue.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkQueue {
  readonly tasks = input.required<TaskDto[]>();
  readonly loading = input<boolean>(false);
  readonly error = input<string | null>(null);

  readonly resolve = output<TaskDto>();
  readonly dismiss = output<number>();

  // Session-lokal, nicht persistiert: "Später" ändert den Task-Status nicht,
  // blendet ihn nur bis zum nächsten Neuladen aus der Sicht aus.
  protected readonly snoozed = signal<Set<number>>(new Set());

  protected readonly visibleTasks = computed((): TaskDto[] => {
    const snoozedIds = this.snoozed();
    return this.tasks().filter((task: TaskDto) => !snoozedIds.has(task.id));
  });

  protected kindLabel(kind: TaskKind): string {
    return KIND_LABELS[kind] ?? kind;
  }

  protected taskSubtitle(task: TaskDto): string | null {
    const context = task.context;
    const title = context['title'];
    if (typeof title === 'string' && title.length > 0) {
      return title;
    }
    const ref = context['ref'];
    if (typeof ref === 'string' && ref.length > 0) {
      return ref;
    }
    return null;
  }

  protected snooze(taskId: number): void {
    this.snoozed.update((current: Set<number>) => new Set(current).add(taskId));
  }
}
