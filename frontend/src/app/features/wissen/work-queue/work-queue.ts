import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import type { TaskDto, TaskKind } from '@photofant/models';
import { Icon } from '../../../ui/icon/icon';

// Fallback-Label für Aufgaben-Arten ohne eigene Label-Logik in `chipLabel` (unverändert
// seit vor P38 Phase 5 — "wie heute" laut Plan).
const KIND_LABELS: Record<TaskKind, string> = {
  new_person: 'Noch kein Wissen angelegt',
  missing_entity: 'Fehlende Entity',
  confirm_relationship: 'Beziehung bestätigen',
  review_recommendation: 'Empfehlung prüfen',
  incomplete_entity: 'Entity noch ohne Inhalt',
  missing_field: 'Feld fehlt',
  low_completeness: 'Kaum ausgefüllt',
  auto_link: 'Verknüpfung vorschlagen',
};

// Nächstliegendes vorhandenes Icon je Aufgaben-Art (Registry hat kein "edit"/"warning").
const KIND_ICONS: Record<TaskKind, string> = {
  new_person: 'user',
  missing_entity: 'info',
  confirm_relationship: 'link',
  review_recommendation: 'sparkle',
  incomplete_entity: 'pencil',
  missing_field: 'pencil',
  low_completeness: 'alertTriangle',
  auto_link: 'link',
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

  protected readonly headline = computed((): string => {
    const count = this.tasks().length;
    return count > 0 ? `Offene Aufgaben · ${count}` : 'Offene Aufgaben';
  });

  protected chipIcon(task: TaskDto): string {
    return KIND_ICONS[task.kind] ?? 'info';
  }

  // P38 Phase 5 — Label/Sub weichen je Aufgaben-Art vom Fallback ab (Design-Kontrakt,
  // `phase-5-wissen-uebersicht.md` „Aufgabe 3"). Bestehende Arten bleiben unverändert.
  protected chipLabel(task: TaskDto): string {
    const context = task.context;
    switch (task.kind) {
      case 'missing_field': {
        const fields = this.stringArray(context['fields']);
        if (fields.length === 0) { return 'Merkmal fehlt'; }
        return fields.length === 1 ? `${fields[0]} fehlt` : `${fields.join(', ')} fehlen`;
      }
      case 'low_completeness': {
        const completeness = typeof context['completeness'] === 'number' ? context['completeness'] : 0;
        return `Profil kaum ausgefüllt (${Math.round(completeness * 100)} %)`;
      }
      case 'auto_link': {
        const title = typeof context['title'] === 'string' ? context['title'] : '';
        const personName = typeof context['person_name'] === 'string' ? context['person_name'] : '';
        return `Notiz „${title}" ähnelt Person ${personName}`;
      }
      default:
        return KIND_LABELS[task.kind] ?? task.kind;
    }
  }

  protected chipSubtitle(task: TaskDto): string | null {
    const context = task.context;
    switch (task.kind) {
      case 'missing_field':
      case 'low_completeness': {
        const title = context['title'];
        return typeof title === 'string' ? title : null;
      }
      case 'auto_link': {
        const score = typeof context['score'] === 'number' ? context['score'] : 0;
        return `${Math.round(score * 100)} % Namens-Übereinstimmung — verknüpfen?`;
      }
      default: {
        const title = context['title'];
        if (typeof title === 'string' && title.length > 0) { return title; }
        const ref = context['ref'];
        if (typeof ref === 'string' && ref.length > 0) { return ref; }
        return null;
      }
    }
  }

  private stringArray(value: unknown): string[] {
    return Array.isArray(value) ? value.filter((item: unknown): item is string => typeof item === 'string') : [];
  }

  protected onDismiss(event: MouseEvent, taskId: number): void {
    event.stopPropagation();
    this.dismiss.emit(taskId);
  }
}
