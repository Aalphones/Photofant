import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Icon } from '@photofant/ui';
import { ERROR_CODE_MESSAGES, ROLE_META } from '@photofant/models';
import type { ComponentSpec, ModelBindError, ModelView } from '@photofant/models';

@Component({
  selector: 'pf-bind-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, FormsModule],
  templateUrl: './bind-dialog.html',
  styleUrl: './bind-dialog.scss',
})
export class BindDialog {
  readonly model = input.required<ModelView>();
  readonly bindError = input<ModelBindError | null>(null);
  readonly bindWarnings = input<string[]>([]);
  readonly isPending = input<boolean>(false);
  readonly confirm = output<{ model: ModelView; path: string }>();
  readonly confirmComponents = output<{ model: ModelView; components: Record<string, string> }>();
  readonly cancel = output<void>();

  protected readonly path = signal<string>('');
  protected readonly componentPaths = signal<Record<string, string>>({});

  protected readonly roleMeta = computed(() =>
    ROLE_META[this.model().role] ?? { icon: 'model', label: this.model().role }
  );

  protected readonly isComponentModel = computed((): boolean => {
    const caps = this.model().capabilities as Record<string, unknown> | null;
    return caps !== null && caps !== undefined && Boolean(caps['component_model']);
  });

  protected readonly componentSpecs = computed((): Array<{ key: string; spec: ComponentSpec }> => {
    const caps = this.model().capabilities as Record<string, unknown> | null;
    if (caps === null || caps === undefined) { return []; }
    const components = caps['components'] as Record<string, ComponentSpec> | undefined;
    if (components === undefined) { return []; }
    return Object.entries(components).map(([key, spec]: [string, ComponentSpec]) => ({ key, spec }));
  });

  protected readonly canConfirm = computed(() => {
    if (this.isPending()) { return false; }
    if (this.isComponentModel()) {
      const paths = this.componentPaths();
      return this.componentSpecs()
        .filter((entry: { key: string; spec: ComponentSpec }) => entry.spec.required)
        .every((entry: { key: string; spec: ComponentSpec }) => (paths[entry.key] ?? '').trim().length > 0);
    }
    return this.path().trim().length > 0;
  });

  protected readonly errorMessage = computed(() => {
    const error = this.bindError();
    if (error === null || error.manifestId !== this.model().id) { return null; }
    return ERROR_CODE_MESSAGES[error.code] ?? error.message;
  });

  protected updateComponentPath(key: string, value: string): void {
    this.componentPaths.update((current: Record<string, string>) => ({ ...current, [key]: value }));
  }

  protected handleConfirm(): void {
    if (!this.canConfirm()) { return; }
    if (this.isComponentModel()) {
      this.confirmComponents.emit({ model: this.model(), components: this.componentPaths() });
    } else {
      this.confirm.emit({ model: this.model(), path: this.path().trim() });
    }
  }

  protected handleCancel(): void { this.cancel.emit(); }
  protected handleScrimClick(): void { this.cancel.emit(); }
}
