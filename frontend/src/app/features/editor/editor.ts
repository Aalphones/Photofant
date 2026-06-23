import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Store } from '@ngrx/store';
import { DOCUMENT } from '@angular/common';
import { Icon } from '@photofant/ui';
import { editorActions, editorSelectors, modelsActions, modelsSelectors } from '@photofant/store';
import type { CropRatio, CropRect, EditorTargetKind } from '@photofant/models';
import { ZoomStage } from '../galerie/lightbox/zoom-stage';
import { BasisPanel } from './basis-panel/basis-panel';
import type { OpEvent } from './basis-panel/basis-panel';
import { Flux2Panel } from './flux2-panel/flux2-panel';
import type { FluxEditEvent } from './flux2-panel/flux2-panel';
import { InpaintPanel } from './inpaint-panel/inpaint-panel';
import type { InpaintEvent } from './inpaint-panel/inpaint-panel';
import { MaskOverlay } from './mask-overlay/mask-overlay';
import { CropOverlay } from './crop-overlay/crop-overlay';
import { StepBar } from './step-bar/step-bar';
import { SaveModal } from './save-modal/save-modal';
import type { SaveMode } from './save-modal/save-modal';

@Component({
  selector: 'pf-editor',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, ZoomStage, BasisPanel, Flux2Panel, InpaintPanel, MaskOverlay, CropOverlay, StepBar, SaveModal],
  templateUrl: './editor.html',
  styleUrl: './editor.scss',
})
export class Editor {
  private readonly store = inject(Store);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly sessionKey = this.store.selectSignal(editorSelectors.selectSessionKey);
  protected readonly steps = this.store.selectSignal(editorSelectors.selectSteps);
  protected readonly currentSeq = this.store.selectSignal(editorSelectors.selectCurrentSeq);
  protected readonly originalPreviewUrl = this.store.selectSignal(editorSelectors.selectOriginalPreviewUrl);
  protected readonly applying = this.store.selectSignal(editorSelectors.selectApplying);
  protected readonly error = this.store.selectSignal(editorSelectors.selectError);
  protected readonly currentPreviewUrl = this.store.selectSignal(editorSelectors.selectCurrentPreviewUrl);
  protected readonly hasUnsavedSteps = this.store.selectSignal(editorSelectors.selectHasUnsavedSteps);
  protected readonly capabilities = this.store.selectSignal(modelsSelectors.selectCapabilities);

  protected readonly generating = this.store.selectSignal(editorSelectors.selectGenerating);

  protected readonly histOpen = signal(true);
  protected readonly showSaveModal = signal(false);
  protected readonly activeTool = signal<'basis' | 'flux2' | 'inpaint'>('basis');
  protected readonly compareMode = signal(false);
  protected readonly maskDataUrl = signal<string | null>(null);

  protected readonly maskOverlayRef = viewChild<MaskOverlay>('maskOverlay');

  protected readonly hasFluxEdit = computed((): boolean => this.capabilities()?.flux_edit === true);
  protected readonly hasInpaint = computed((): boolean => this.capabilities()?.inpaint === true);
  protected readonly isInpaintMode = computed((): boolean => this.activeTool() === 'inpaint');

  protected readonly cropActive = signal(false);
  protected readonly cropRect = signal<CropRect>({ x: 0, y: 0, w: 100, h: 100 });
  protected readonly cropRatio = signal<CropRatio>('free');

  protected readonly zoomInteractive = computed((): boolean => !this.cropActive());

  protected readonly displayImageUrl = computed((): string =>
    this.currentPreviewUrl() ?? ''
  );

  protected readonly hasSteps = computed((): boolean => this.steps().length > 0);

  constructor() {
    const params = this.route.snapshot.params;
    const kind = params['kind'] as EditorTargetKind;
    const id = Number(params['id']);

    this.store.dispatch(editorActions.init({ kind, id }));
    this.store.dispatch(modelsActions.loadCapabilities());

    const keyHandler = (event: KeyboardEvent): void => {
      const target = event.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') { return; }
      if (event.key === 'Escape') {
        if (this.cropActive()) {
          this.cropActive.set(false);
        } else if (this.showSaveModal()) {
          this.showSaveModal.set(false);
        } else {
          this.goBack();
        }
      }
      if ((event.metaKey || event.ctrlKey) && event.key === 's') {
        event.preventDefault();
        this.showSaveModal.set(true);
      }
      if ((event.metaKey || event.ctrlKey) && event.key === 'z') {
        event.preventDefault();
        const seq = this.currentSeq();
        if (seq > 0) {
          this.store.dispatch(editorActions.rollback({ toSeq: seq - 1 }));
        }
      }
    };
    this.document.addEventListener('keydown', keyHandler);
    this.destroyRef.onDestroy(() => {
      this.document.removeEventListener('keydown', keyHandler);
      this.store.dispatch(editorActions.close());
    });

    effect((): void => {
      const error = this.error();
      if (error != null) {
        console.error('[Editor]', error);
      }
    });
  }

  protected goBack(): void {
    this.router.navigate(['/galerie']);
  }

  protected toggleHist(): void {
    this.histOpen.update((open: boolean) => !open);
  }

  protected toggleCompare(): void {
    this.compareMode.update((on: boolean) => !on);
  }

  protected onActivateCrop(): void {
    this.cropActive.set(true);
    this.cropRect.set({ x: 0, y: 0, w: 100, h: 100 });
  }

  protected onDeactivateCrop(): void {
    this.cropActive.set(false);
  }

  protected onCropRatioChange(ratio: CropRatio): void {
    this.cropRatio.set(ratio);
  }

  protected onCropRectChange(rect: CropRect): void {
    this.cropRect.set(rect);
  }

  protected onApplyOp(event: OpEvent): void {
    if (event.op === 'crop') {
      this.cropActive.set(false);
    }
    this.store.dispatch(editorActions.applyStep({
      op: event.op,
      params: event.params,
      label: event.label,
    }));
  }

  protected onRollback(seq: number): void {
    this.store.dispatch(editorActions.rollback({ toSeq: seq }));
  }

  protected onSave(mode: SaveMode): void {
    this.showSaveModal.set(false);
    console.info('[Editor] Save requested:', mode);
  }

  protected setTool(tool: 'basis' | 'flux2' | 'inpaint'): void {
    this.activeTool.set(tool);
    if (tool !== 'inpaint') {
      this.maskDataUrl.set(null);
      this.maskOverlayRef()?.clearMask();
    }
  }

  protected onFluxEdit(event: FluxEditEvent): void {
    this.store.dispatch(editorActions.fluxEdit({
      prompt: event.prompt,
      templateId: event.templateId,
      params: event.params,
    }));
  }

  protected onInpaint(event: InpaintEvent): void {
    this.store.dispatch(editorActions.inpaint({
      mask: event.mask,
      prompt: event.prompt,
      params: event.params,
    }));
  }

  protected onMaskChanged(dataUrl: string | null): void {
    this.maskDataUrl.set(dataUrl);
  }

  protected onBrushSizeChange(_size: number): void {
    // propagated to mask overlay via input binding
  }

  protected onClearMask(): void {
    this.maskOverlayRef()?.clearMask();
    this.maskDataUrl.set(null);
  }
}
