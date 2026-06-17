import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { Icon } from '@photofant/ui';
import { ROLE_META, formatModelSize } from '@photofant/models';
import type { ModelView } from '@photofant/models';

@Component({
  selector: 'pf-download-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './download-dialog.html',
  styleUrl: './download-dialog.scss',
})
export class DownloadDialog {
  readonly model = input.required<ModelView>();
  readonly modelsDir = input<string | null>(null);
  readonly confirm = output<{ model: ModelView; licenseAck: boolean }>();
  readonly cancel = output<void>();

  protected readonly licenseAgreed = signal<boolean>(false);
  protected readonly roleMeta = computed(() =>
    ROLE_META[this.model().role] ?? { icon: 'model', label: this.model().role }
  );
  protected readonly isDisabled = computed(() =>
    this.model().licenseNc && !this.licenseAgreed()
  );
  protected readonly targetPath = computed(() => {
    const dir = this.modelsDir() ?? '~/photofant/models';
    return `${dir}/${this.model().id}`;
  });

  protected toggleLicense(): void {
    this.licenseAgreed.update((agreed: boolean) => !agreed);
  }

  protected handleConfirm(): void {
    if (this.isDisabled()) { return; }
    this.confirm.emit({ model: this.model(), licenseAck: this.licenseAgreed() || !this.model().licenseNc });
  }

  protected handleCancel(): void { this.cancel.emit(); }
  protected handleScrimClick(): void { this.cancel.emit(); }

  protected formatSize(bytes: number | null): string {
    return formatModelSize(bytes);
  }
}
