import { ChangeDetectionStrategy, Component, output, signal } from '@angular/core';
import { Icon } from '@photofant/ui';

export interface OpEvent {
  op: string;
  params: Record<string, unknown>;
  label: string;
}

type CropRatio = 'free' | '1:1' | '4:3' | '3:4' | '16:9' | '3:2' | '2:3';
type ConvertFormat = 'keep' | 'png' | 'jpeg';

interface RatioOption { id: CropRatio; label: string }

const RATIOS: RatioOption[] = [
  { id: 'free', label: 'Frei' },
  { id: '1:1', label: '1:1' },
  { id: '4:3', label: '4:3' },
  { id: '3:4', label: '3:4' },
  { id: '16:9', label: '16:9' },
  { id: '3:2', label: '3:2' },
  { id: '2:3', label: '2:3' },
];

@Component({
  selector: 'pf-basis-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './basis-panel.html',
  styleUrl: './basis-panel.scss',
})
export class BasisPanel {
  readonly applyOp = output<OpEvent>();

  protected readonly cropRatio = signal<CropRatio>('free');
  protected readonly convertFormat = signal<ConvertFormat>('keep');
  protected readonly jpegQuality = signal(92);
  protected readonly ratios = RATIOS;

  protected setCropRatio(ratio: CropRatio): void {
    this.cropRatio.set(ratio);
  }

  protected setConvertFormat(format: ConvertFormat): void {
    this.convertFormat.set(format);
  }

  protected setJpegQuality(value: number): void {
    this.jpegQuality.set(value);
  }

  protected applyCrop(): void {
    const ratio = this.cropRatio();
    this.applyOp.emit({
      op: 'crop',
      params: { ratio, x: 10, y: 10, w: 80, h: 80 },
      label: `Zugeschnitten (${ratio === 'free' ? 'Frei' : ratio})`,
    });
  }

  protected applySmartCrop(): void {
    this.applyOp.emit({ op: 'smart_crop', params: {}, label: 'Smart-Crop (Gesicht)' });
  }

  protected applyRotate(direction: 'cw' | 'ccw' | '180'): void {
    const labels: Record<string, string> = { cw: '+90°', ccw: '−90°', '180': '180°' };
    this.applyOp.emit({ op: 'rotate', params: { dir: direction }, label: labels[direction] ?? direction });
  }

  protected applyMirror(axis: 'h' | 'v'): void {
    this.applyOp.emit({
      op: 'mirror',
      params: { axis },
      label: axis === 'h' ? 'Horizontal spiegeln' : 'Vertikal spiegeln',
    });
  }

  protected applyPad(): void {
    this.applyOp.emit({ op: 'pad', params: {}, label: 'Auf Quadrat aufgefüllt' });
  }

  protected applyConvert(): void {
    const format = this.convertFormat();
    const quality = this.jpegQuality();
    const label = format === 'keep'
      ? 'Format beibehalten'
      : `Konvertiert → ${format.toUpperCase()}${format === 'jpeg' ? ` Q${quality}` : ''}`;
    this.applyOp.emit({ op: 'convert', params: { format, quality }, label });
  }
}
