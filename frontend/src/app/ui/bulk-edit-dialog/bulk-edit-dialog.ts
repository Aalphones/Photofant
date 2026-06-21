import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { Icon } from '../icon/icon';

export interface BulkEditPayload {
  op: string;
  params: Record<string, unknown>;
}

type BulkOp = 'rotate' | 'mirror' | 'convert' | 'rembg';

interface OpOption {
  key: BulkOp;
  label: string;
  desc: string;
}

const ALL_OPS: OpOption[] = [
  { key: 'rotate',  label: 'Drehen',            desc: '90°, 180° oder Spiegelverkehrt' },
  { key: 'mirror',  label: 'Spiegeln',           desc: 'Horizontal oder vertikal' },
  { key: 'convert', label: 'Konvertieren',       desc: 'PNG ↔ JPEG (inkl. Qualitätsstufe)' },
  { key: 'rembg',   label: 'Hintergrund entfernen', desc: 'u2net ONNX — Modell muss aktiv sein' },
];

@Component({
  selector: 'pf-bulk-edit-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './bulk-edit-dialog.html',
  styleUrl: './bulk-edit-dialog.scss',
})
export class BulkEditDialog {
  readonly scopeLabel = input.required<string>();
  readonly confirm = output<BulkEditPayload>();
  readonly cancel = output<void>();

  protected readonly OPS = ALL_OPS;

  protected readonly selectedOp = signal<BulkOp>('rotate');
  protected readonly rotateDir = signal<'cw' | 'ccw' | '180'>('cw');
  protected readonly mirrorAxis = signal<'h' | 'v'>('h');
  protected readonly convertFormat = signal<'jpeg' | 'png'>('jpeg');
  protected readonly convertQuality = signal<number>(92);

  protected readonly currentParams = computed((): Record<string, unknown> => {
    const op = this.selectedOp();
    if (op === 'rotate') {
      return { dir: this.rotateDir() };
    }
    if (op === 'mirror') {
      return { axis: this.mirrorAxis() };
    }
    if (op === 'convert') {
      const format = this.convertFormat();
      return format === 'jpeg'
        ? { format, quality: this.convertQuality() }
        : { format };
    }
    return {};
  });

  protected selectOp(op: BulkOp): void {
    this.selectedOp.set(op);
  }

  protected onQualityInput(event: Event): void {
    const value = parseInt((event.target as HTMLInputElement).value, 10);
    if (!isNaN(value)) {
      this.convertQuality.set(Math.max(1, Math.min(100, value)));
    }
  }

  protected handleConfirm(): void {
    this.confirm.emit({ op: this.selectedOp(), params: this.currentParams() });
  }

  protected handleCancel(): void {
    this.cancel.emit();
  }

  protected handleScrimClick(): void {
    this.cancel.emit();
  }
}
