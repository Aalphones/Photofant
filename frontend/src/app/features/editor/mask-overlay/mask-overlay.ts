import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  effect,
  ElementRef,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';

@Component({
  selector: 'pf-mask-overlay',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './mask-overlay.html',
  styleUrl: './mask-overlay.scss',
})
export class MaskOverlay implements AfterViewInit {
  readonly imageUrl = input.required<string>();
  readonly brushSize = input(30);
  readonly brushMode = input<'paint' | 'erase'>('paint');

  readonly maskChanged = output<string | null>();

  private readonly canvasRef = viewChild.required<ElementRef<HTMLCanvasElement>>('maskCanvas');
  private context: CanvasRenderingContext2D | null = null;
  private painting = false;
  private lastPoint: { x: number; y: number } | null = null;
  private hasContent = false;

  protected readonly cursorSize = signal(30);

  constructor() {
    effect((): void => {
      this.cursorSize.set(this.brushSize());
    });
  }

  ngAfterViewInit(): void {
    const canvas = this.canvasRef().nativeElement;
    this.context = canvas.getContext('2d');
    this.fitToParent();
  }

  private fitToParent(): void {
    const canvas = this.canvasRef().nativeElement;
    const parent = canvas.parentElement;
    if (parent == null) { return; }
    canvas.width = parent.clientWidth;
    canvas.height = parent.clientHeight;
  }

  clearMask(): void {
    const canvas = this.canvasRef().nativeElement;
    const context = this.context;
    if (context == null) { return; }
    context.clearRect(0, 0, canvas.width, canvas.height);
    this.hasContent = false;
    this.maskChanged.emit(null);
  }

  exportMask(): string | null {
    if (!this.hasContent) { return null; }
    const canvas = this.canvasRef().nativeElement;
    return canvas.toDataURL('image/png');
  }

  protected onPointerDown(event: PointerEvent): void {
    event.preventDefault();
    const canvas = this.canvasRef().nativeElement;
    canvas.setPointerCapture(event.pointerId);
    this.painting = true;
    this.lastPoint = this.getCanvasPoint(event);
    this.drawDot(this.lastPoint);
  }

  protected onPointerMove(event: PointerEvent): void {
    if (!this.painting) { return; }
    const current = this.getCanvasPoint(event);
    if (this.lastPoint != null) {
      this.drawLine(this.lastPoint, current);
    }
    this.lastPoint = current;
  }

  protected onPointerUp(): void {
    this.painting = false;
    this.lastPoint = null;
    this.emitMask();
  }

  private getCanvasPoint(event: PointerEvent): { x: number; y: number } {
    const canvas = this.canvasRef().nativeElement;
    const rect = canvas.getBoundingClientRect();
    return {
      x: (event.clientX - rect.left) * (canvas.width / rect.width),
      y: (event.clientY - rect.top) * (canvas.height / rect.height),
    };
  }

  private drawDot(point: { x: number; y: number }): void {
    const context = this.context;
    if (context == null) { return; }
    const radius = this.brushSize() / 2;
    this.applyBrushMode(context);
    context.beginPath();
    context.arc(point.x, point.y, radius, 0, Math.PI * 2);
    context.fill();
    this.hasContent = true;
  }

  private drawLine(from: { x: number; y: number }, to: { x: number; y: number }): void {
    const context = this.context;
    if (context == null) { return; }
    this.applyBrushMode(context);
    context.lineWidth = this.brushSize();
    context.lineCap = 'round';
    context.lineJoin = 'round';
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.stroke();
    this.hasContent = true;
  }

  private applyBrushMode(context: CanvasRenderingContext2D): void {
    if (this.brushMode() === 'erase') {
      context.globalCompositeOperation = 'destination-out';
      context.fillStyle = 'rgba(0,0,0,1)';
      context.strokeStyle = 'rgba(0,0,0,1)';
    } else {
      context.globalCompositeOperation = 'source-over';
      context.fillStyle = 'rgba(255, 80, 80, 0.5)';
      context.strokeStyle = 'rgba(255, 80, 80, 0.5)';
    }
  }

  private emitMask(): void {
    this.maskChanged.emit(this.exportMask());
  }
}
