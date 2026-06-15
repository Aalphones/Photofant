import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  signal,
  viewChild,
  ElementRef,
  effect,
} from '@angular/core';
import { Icon } from '@photofant/ui';

@Component({
  selector: 'pf-zoom-stage',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon],
  templateUrl: './zoom-stage.html',
  styleUrl: './zoom-stage.scss',
})
export class ZoomStage {
  private readonly destroyRef = inject(DestroyRef);

  readonly imageUrl = input.required<string>();

  private readonly wrapEl = viewChild.required<ElementRef<HTMLDivElement>>('wrapEl');
  private readonly innerEl = viewChild.required<ElementRef<HTMLDivElement>>('innerEl');

  private scale = 1;
  private translateX = 0;
  private translateY = 0;
  private readonly MAX_ZOOM = 6;
  private readonly pointers = new Map<number, { x: number; y: number }>();
  private pinchDist: number | null = null;

  protected readonly displayScale = signal(1);
  protected readonly isZoomed = computed(() => this.displayScale() > 1.001);
  protected readonly zoomPercent = computed(() => Math.round(this.displayScale() * 100));

  constructor() {
    afterNextRender(() => {
      const wrap = this.wrapEl().nativeElement;
      const wheelHandler = (event: WheelEvent): void => {
        event.preventDefault();
        const rect = wrap.getBoundingClientRect();
        const factor = event.deltaY < 0 ? 1.2 : 1 / 1.2;
        this.zoomAt(event.clientX - rect.left, event.clientY - rect.top, factor);
      };
      wrap.addEventListener('wheel', wheelHandler, { passive: false });
      this.destroyRef.onDestroy(() => wrap.removeEventListener('wheel', wheelHandler));
    });

    effect(() => {
      this.imageUrl();
      this.resetZoom();
    });
  }

  private resetZoom(): void {
    this.scale = 1;
    this.translateX = 0;
    this.translateY = 0;
    this.displayScale.set(1);
    const innerRef = this.innerEl;
    try {
      const inner = innerRef()?.nativeElement;
      if (inner) inner.style.transform = '';
    } catch {
      // view not yet initialized — reset will apply on next render
    }
  }

  private applyTransform(): void {
    const inner = this.innerEl().nativeElement;
    inner.style.transform = `translate(${this.translateX}px, ${this.translateY}px) scale(${this.scale})`;
    this.displayScale.set(this.scale);
  }

  private clampTranslation(): void {
    const rect = this.wrapEl().nativeElement.getBoundingClientRect();
    const minX = rect.width - this.scale * rect.width;
    const minY = rect.height - this.scale * rect.height;
    this.translateX = Math.min(0, Math.max(minX, this.translateX));
    this.translateY = Math.min(0, Math.max(minY, this.translateY));
  }

  protected reset(): void {
    this.scale = 1;
    this.translateX = 0;
    this.translateY = 0;
    this.applyTransform();
  }

  private zoomAt(cx: number, cy: number, factor: number): void {
    const oldScale = this.scale;
    const newScale = Math.min(this.MAX_ZOOM, Math.max(1, oldScale * factor));
    if (newScale === oldScale) return;
    this.translateX = cx - (newScale / oldScale) * (cx - this.translateX);
    this.translateY = cy - (newScale / oldScale) * (cy - this.translateY);
    this.scale = newScale;
    if (newScale <= 1.001) {
      this.translateX = 0;
      this.translateY = 0;
    }
    this.clampTranslation();
    this.applyTransform();
  }

  protected onPointerDown(event: PointerEvent): void {
    this.wrapEl().nativeElement.setPointerCapture(event.pointerId);
    this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (this.pointers.size === 2) {
      const pts = [...this.pointers.values()];
      const p0 = pts[0]!; // size === 2 guarantees both slots exist
      const p1 = pts[1]!;
      this.pinchDist = Math.hypot(p0.x - p1.x, p0.y - p1.y);
    }
  }

  protected onPointerMove(event: PointerEvent): void {
    const prev = this.pointers.get(event.pointerId);
    if (!prev) return;
    this.pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const pts = [...this.pointers.values()];
    if (pts.length >= 2 && pts[0] !== undefined && pts[1] !== undefined) {
      const rect = this.wrapEl().nativeElement.getBoundingClientRect();
      const dist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      if (this.pinchDist != null) {
        const mx = (pts[0].x + pts[1].x) / 2 - rect.left;
        const my = (pts[0].y + pts[1].y) / 2 - rect.top;
        this.zoomAt(mx, my, dist / this.pinchDist);
      }
      this.pinchDist = dist;
    } else if (this.scale > 1) {
      this.translateX += event.clientX - prev.x;
      this.translateY += event.clientY - prev.y;
      this.clampTranslation();
      this.applyTransform();
    }
  }

  protected onPointerUp(event: PointerEvent): void {
    this.pointers.delete(event.pointerId);
    if (this.pointers.size < 2) this.pinchDist = null;
  }

  protected onDoubleClick(event: MouseEvent): void {
    if (this.scale > 1) {
      this.reset();
      return;
    }
    const rect = this.wrapEl().nativeElement.getBoundingClientRect();
    this.zoomAt(event.clientX - rect.left, event.clientY - rect.top, 2.6);
  }
}
