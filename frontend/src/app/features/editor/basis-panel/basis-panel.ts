import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';
import { Icon } from '@photofant/ui';
import type { CropRatio, CropRect } from '@photofant/models';

export interface OpEvent {
  op: string;
  params: Record<string, unknown>;
  label: string;
}

type ConvertFormat = 'keep' | 'png' | 'jpeg';
type PadColor = '#000000' | '#ffffff' | 'transparent';

interface RatioOption { id: CropRatio; label: string }
interface PadRatioOption { id: string; label: string }

const CROP_RATIOS: RatioOption[] = [
  { id: 'free', label: 'Frei' },
  { id: '1:1', label: '1:1' },
  { id: '4:3', label: '4:3' },
  { id: '3:4', label: '3:4' },
  { id: '16:9', label: '16:9' },
  { id: '3:2', label: '3:2' },
  { id: '2:3', label: '2:3' },
];

const PAD_RATIOS: PadRatioOption[] = [
  { id: '1:1', label: '1:1' },
  { id: '4:3', label: '4:3' },
  { id: '16:9', label: '16:9' },
  { id: '3:2', label: '3:2' },
];

@Component({
  selector: 'pf-basis-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './basis-panel.html',
  styleUrl: './basis-panel.scss',
})
export class BasisPanel {
  readonly cropActive = input(false);
  readonly cropRect = input<CropRect>({ x: 0, y: 0, w: 100, h: 100 });
  readonly cropRatio = input<CropRatio>('free');

  readonly applyOp = output<OpEvent>();
  readonly activateCrop = output<void>();
  readonly deactivateCrop = output<void>();
  readonly cropRatioChange = output<CropRatio>();

  protected readonly ratios = CROP_RATIOS;
  protected readonly padRatios = PAD_RATIOS;
  protected readonly convertFormat = signal<ConvertFormat>('keep');
  protected readonly jpegQuality = signal(92);
  protected readonly padTarget = signal('1:1');
  protected readonly padColor = signal<PadColor>('#000000');
  protected readonly freeAngle = signal(0);

  protected onSelectCropRatio(ratio: CropRatio): void {
    this.cropRatioChange.emit(ratio);
    if (!this.cropActive()) {
      this.activateCrop.emit();
    }
  }

  protected onStartCrop(): void {
    this.activateCrop.emit();
  }

  protected applyCrop(): void {
    const rect = this.cropRect();
    const ratio = this.cropRatio();
    this.applyOp.emit({
      op: 'crop',
      params: { x: rect.x, y: rect.y, w: rect.w, h: rect.h },
      label: `Zugeschnitten (${ratio === 'free' ? 'Frei' : ratio})`,
    });
    this.deactivateCrop.emit();
  }

  protected applySmartCrop(): void {
    this.applyOp.emit({ op: 'smart_crop', params: {}, label: 'Smart-Crop (Gesicht)' });
  }

  protected applyRotate(direction: 'cw' | 'ccw' | '180'): void {
    const labels: Record<string, string> = { cw: '+90°', ccw: '−90°', '180': '180°' };
    this.applyOp.emit({ op: 'rotate', params: { dir: direction }, label: labels[direction] ?? direction });
  }

  protected applyFreeRotate(): void {
    const angle = this.freeAngle();
    if (angle === 0) { return; }
    this.applyOp.emit({
      op: 'rotate',
      params: { dir: 'free', angle },
      label: `Frei ${angle > 0 ? '+' : ''}${angle}°`,
    });
    this.freeAngle.set(0);
  }

  protected setFreeAngle(value: number): void {
    this.freeAngle.set(value);
  }

  protected applyMirror(axis: 'h' | 'v'): void {
    this.applyOp.emit({
      op: 'mirror',
      params: { axis },
      label: axis === 'h' ? 'Horizontal spiegeln' : 'Vertikal spiegeln',
    });
  }

  protected setPadTarget(target: string): void {
    this.padTarget.set(target);
  }

  protected setPadColor(color: PadColor): void {
    this.padColor.set(color);
  }

  protected applyPad(): void {
    const target = this.padTarget();
    const color = this.padColor();
    const colorLabel = color === '#000000' ? 'Schwarz' : color === '#ffffff' ? 'Weiß' : 'Transparent';
    this.applyOp.emit({
      op: 'pad',
      params: { target, color },
      label: `Padding ${target} (${colorLabel})`,
    });
  }

  protected setConvertFormat(format: ConvertFormat): void {
    this.convertFormat.set(format);
  }

  protected setJpegQuality(value: number): void {
    this.jpegQuality.set(value);
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
