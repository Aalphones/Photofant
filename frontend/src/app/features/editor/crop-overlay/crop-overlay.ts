import {
  afterNextRender,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { DOCUMENT } from '@angular/common';
import type { CropRatio, CropRect } from '@photofant/models';

type HandleId = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w';
type DragType = 'move' | HandleId;

interface ImageBounds {
  offsetX: number;
  offsetY: number;
  renderW: number;
  renderH: number;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function clampRect(rect: CropRect): CropRect {
  const w = clamp(rect.w, 2, 100);
  const h = clamp(rect.h, 2, 100);
  const x = clamp(rect.x, 0, 100 - w);
  const y = clamp(rect.y, 0, 100 - h);
  return { x, y, w, h };
}

function parseRatio(ratio: CropRatio): number | null {
  if (ratio === 'free') { return null; }
  const parts = ratio.split(':');
  if (parts.length !== 2) { return null; }
  const ratioW = parseInt(parts[0]!, 10);
  const ratioH = parseInt(parts[1]!, 10);
  if (isNaN(ratioW) || isNaN(ratioH) || ratioH === 0) { return null; }
  return ratioW / ratioH;
}

@Component({
  selector: 'pf-crop-overlay',
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './crop-overlay.html',
  styleUrl: './crop-overlay.scss',
})
export class CropOverlay {
  private readonly hostEl = inject(ElementRef<HTMLElement>);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);

  readonly imageUrl = input.required<string>();
  readonly ratio = input<CropRatio>('free');
  readonly rect = input.required<CropRect>();
  readonly rectChange = output<CropRect>();

  private readonly containerSize = signal({ w: 0, h: 0 });
  private readonly naturalSize = signal({ w: 0, h: 0 });

  protected readonly imageBounds = computed((): ImageBounds => {
    const container = this.containerSize();
    const natural = this.naturalSize();
    if (container.w === 0 || container.h === 0 || natural.w === 0 || natural.h === 0) {
      return { offsetX: 0, offsetY: 0, renderW: 0, renderH: 0 };
    }
    const imgAspect = natural.w / natural.h;
    const containerAspect = container.w / container.h;
    if (imgAspect > containerAspect) {
      const renderW = container.w;
      const renderH = container.w / imgAspect;
      return { offsetX: 0, offsetY: (container.h - renderH) / 2, renderW, renderH };
    }
    const renderH = container.h;
    const renderW = container.h * imgAspect;
    return { offsetX: (container.w - renderW) / 2, offsetY: 0, renderW, renderH };
  });

  protected readonly cropScreen = computed(() => {
    const bounds = this.imageBounds();
    const crop = this.rect();
    return {
      left: bounds.offsetX + (crop.x / 100) * bounds.renderW,
      top: bounds.offsetY + (crop.y / 100) * bounds.renderH,
      width: (crop.w / 100) * bounds.renderW,
      height: (crop.h / 100) * bounds.renderH,
    };
  });

  protected readonly handles: HandleId[] = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];

  private dragType: DragType | null = null;
  private dragStartX = 0;
  private dragStartY = 0;
  private dragStartRect: CropRect = { x: 0, y: 0, w: 100, h: 100 };

  constructor() {
    afterNextRender(() => {
      const host = this.hostEl.nativeElement;
      const observer = new ResizeObserver((entries: ResizeObserverEntry[]) => {
        const entry = entries[0];
        if (entry) {
          this.containerSize.set({ w: entry.contentRect.width, h: entry.contentRect.height });
        }
      });
      observer.observe(host);
      this.destroyRef.onDestroy(() => observer.disconnect());
    });

    effect(() => {
      const url = this.imageUrl();
      if (!url) { return; }
      const img = new Image();
      img.onload = (): void => {
        this.naturalSize.set({ w: img.naturalWidth, h: img.naturalHeight });
      };
      img.src = url;
    });

    // Snap bei Ratio-Wechsel — und nachgeholt, sobald die Bildgröße geladen ist
    // (beim Klick auf einen Ratio-Button kann das Bild noch laden; effectiveAspect
    // braucht naturalSize, sonst wird der Snap stillschweigend übersprungen).
    let prevRatio: CropRatio | null = null;
    let snappedForRatio: CropRatio | null = null;
    effect(() => {
      const ratio = this.ratio();
      const natural = this.naturalSize();
      const ratioChanged = prevRatio !== null && ratio !== prevRatio;
      prevRatio = ratio;
      if (ratio === 'free') {
        snappedForRatio = ratio;
        return;
      }
      if (natural.w === 0 || natural.h === 0) { return; }
      if (ratioChanged || snappedForRatio !== ratio) {
        this.snapToRatio(ratio);
        snappedForRatio = ratio;
      }
    });

    afterNextRender(() => {
      const keyHandler = (event: KeyboardEvent): void => {
        const target = event.target as HTMLElement;
        if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') { return; }
        const step = event.shiftKey ? 5 : 1;
        const crop = this.rect();
        let updated: CropRect | null = null;
        if (event.key === 'ArrowLeft') {
          updated = { ...crop, x: Math.max(0, crop.x - step) };
        } else if (event.key === 'ArrowRight') {
          updated = { ...crop, x: Math.min(100 - crop.w, crop.x + step) };
        } else if (event.key === 'ArrowUp') {
          updated = { ...crop, y: Math.max(0, crop.y - step) };
        } else if (event.key === 'ArrowDown') {
          updated = { ...crop, y: Math.min(100 - crop.h, crop.y + step) };
        }
        if (updated) {
          event.preventDefault();
          this.rectChange.emit(updated);
        }
      };
      this.document.addEventListener('keydown', keyHandler);
      this.destroyRef.onDestroy(() => this.document.removeEventListener('keydown', keyHandler));
    });
  }

  /**
   * Ziel-Seitenverhältnis in den Prozent-Raum des Rects umrechnen.
   *
   * Rect-Maße (w/h) sind Prozent der gerenderten Bildbreite/-höhe, die je nach
   * Bild-Seitenverhältnis unterschiedliche Pixel-Skalen haben. Ein echtes Pixel-Ratio
   * `target` erfordert daher `w%/h% = target × naturalH / naturalW`. Ohne diese
   * Korrektur stimmt das Verhältnis nur bei quadratischen Bildern.
   */
  private effectiveAspect(ratio: CropRatio): number | null {
    const target = parseRatio(ratio);
    if (target === null) { return null; }
    const natural = this.naturalSize();
    if (natural.w === 0 || natural.h === 0) { return null; }
    return target * natural.h / natural.w;
  }

  private snapToRatio(ratio: CropRatio): void {
    const aspect = this.effectiveAspect(ratio);
    if (aspect === null) { return; }
    const crop = this.rect();
    const currentAspect = crop.w / crop.h;
    let newW: number;
    let newH: number;
    if (currentAspect > aspect) {
      newH = crop.h;
      newW = crop.h * aspect;
    } else {
      newW = crop.w;
      newH = crop.w / aspect;
    }
    this.rectChange.emit(clampRect({
      x: crop.x + (crop.w - newW) / 2,
      y: crop.y + (crop.h - newH) / 2,
      w: newW,
      h: newH,
    }));
  }

  protected onPointerDown(event: PointerEvent, type: DragType): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragType = type;
    this.dragStartX = event.clientX;
    this.dragStartY = event.clientY;
    this.dragStartRect = { ...this.rect() };

    const onMove = (moveEvent: PointerEvent): void => this.onDragMove(moveEvent);
    const onUp = (): void => {
      this.dragType = null;
      this.document.removeEventListener('pointermove', onMove);
      this.document.removeEventListener('pointerup', onUp);
    };
    this.document.addEventListener('pointermove', onMove);
    this.document.addEventListener('pointerup', onUp);
  }

  private onDragMove(event: PointerEvent): void {
    if (this.dragType === null) { return; }
    const bounds = this.imageBounds();
    if (bounds.renderW === 0 || bounds.renderH === 0) { return; }

    const deltaPctX = ((event.clientX - this.dragStartX) / bounds.renderW) * 100;
    const deltaPctY = ((event.clientY - this.dragStartY) / bounds.renderH) * 100;
    const start = this.dragStartRect;

    if (this.dragType === 'move') {
      this.rectChange.emit(clampRect({
        x: start.x + deltaPctX,
        y: start.y + deltaPctY,
        w: start.w,
        h: start.h,
      }));
      return;
    }

    let resized = this.computeResize(start, this.dragType, deltaPctX, deltaPctY);
    const aspect = this.effectiveAspect(this.ratio());
    if (aspect !== null) {
      resized = this.applyRatioConstraint(resized, aspect, this.dragType);
    }
    this.rectChange.emit(clampRect(resized));
  }

  private computeResize(start: CropRect, handle: HandleId, dx: number, dy: number): CropRect {
    let x = start.x;
    let y = start.y;
    let w = start.w;
    let h = start.h;
    const right = start.x + start.w;
    const bottom = start.y + start.h;

    if (handle.includes('w')) { x = start.x + dx; w = right - x; }
    else if (handle.includes('e')) { w = start.w + dx; }

    if (handle.startsWith('n')) { y = start.y + dy; h = bottom - y; }
    else if (handle.startsWith('s')) { h = start.h + dy; }

    if (w < 2) { w = 2; if (handle.includes('w')) { x = right - 2; } }
    if (h < 2) { h = 2; if (handle.startsWith('n')) { y = bottom - 2; } }

    return { x, y, w, h };
  }

  private applyRatioConstraint(rect: CropRect, aspect: number, handle: HandleId): CropRect {
    let { x, y, w, h } = rect;
    if (handle === 'n' || handle === 's') {
      w = h * aspect;
      x = rect.x + (rect.w - w) / 2;
    } else if (handle === 'e' || handle === 'w') {
      h = w / aspect;
      y = rect.y + (rect.h - h) / 2;
    } else {
      const currentAspect = w / h;
      if (currentAspect > aspect) {
        w = h * aspect;
        if (handle.includes('w')) { x = (rect.x + rect.w) - w; }
      } else {
        h = w / aspect;
        if (handle.startsWith('n')) { y = (rect.y + rect.h) - h; }
      }
    }
    return { x, y, w, h };
  }
}
