import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  input,
  OnInit,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Store } from '@ngrx/store';
import { DOCUMENT, NgTemplateOutlet } from '@angular/common';
import { Icon } from '@photofant/ui';
import { comfyuiActions, comfyuiSelectors, editorActions, editorSelectors, modelsActions, modelsSelectors } from '@photofant/store';
import type { ComfyUIWorkflow, CropRatio, CropRect, DefaultRunTask, EditorTargetKind } from '@photofant/models';
import { ZoomStage } from '../galerie/lightbox/zoom-stage';
import { BasisPanel } from './basis-panel/basis-panel';
import type { OpEvent } from './basis-panel/basis-panel';
import { Flux2Panel } from './flux2-panel/flux2-panel';
import type { EditEvent } from './flux2-panel/flux2-panel';
import { InpaintPanel } from './inpaint-panel/inpaint-panel';
import type { InpaintEvent } from './inpaint-panel/inpaint-panel';
import { UpscalePanel } from './upscale-panel/upscale-panel';
import type { UpscaleEvent } from './upscale-panel/upscale-panel';
import { MaskOverlay } from './mask-overlay/mask-overlay';
import { CropOverlay } from './crop-overlay/crop-overlay';
import { StepBar } from './step-bar/step-bar';
import { SaveModal } from './save-modal/save-modal';
import type { SaveMode } from './save-modal/save-modal';

type EditorTool = 'basis' | 'edit' | 'inpaint' | 'upscale';

@Component({
  selector: 'pf-editor',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Icon, RouterLink, NgTemplateOutlet, ZoomStage, BasisPanel, Flux2Panel, InpaintPanel, UpscalePanel, MaskOverlay, CropOverlay, StepBar, SaveModal],
  templateUrl: './editor.html',
  styleUrl: './editor.scss',
  host: { '[class.modal-mode]': 'modal()' },
})
export class Editor implements OnInit {
  private readonly store = inject(Store);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly document = inject(DOCUMENT);
  private readonly destroyRef = inject(DestroyRef);

  // Modal-Modus: vom Parent (z.B. Lightbox) eingebettet statt als Route geöffnet
  readonly modal = input(false);
  readonly modalKind = input<EditorTargetKind | null>(null);
  readonly modalId = input<number | null>(null);
  readonly closed = output<void>();

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
  protected readonly generativeResult = this.store.selectSignal(editorSelectors.selectGenerativeResult);
  protected readonly generativeSelected = this.store.selectSignal(editorSelectors.selectGenerativeSelected);

  // ── Generative Tools über ComfyUI-Default-Workflows ──
  protected readonly comfyConfig = this.store.selectSignal(comfyuiSelectors.selectConfig);
  private readonly activeWorkflows = this.store.selectSignal(comfyuiSelectors.selectActiveWorkflows);

  protected readonly editWorkflow = computed((): ComfyUIWorkflow | null =>
    this.findDefaultWorkflow(this.comfyConfig().defaultEdit)
  );
  protected readonly inpaintWorkflow = computed((): ComfyUIWorkflow | null =>
    this.findDefaultWorkflow(this.comfyConfig().defaultInpaint)
  );
  protected readonly upscaleWorkflow = computed((): ComfyUIWorkflow | null =>
    this.findDefaultWorkflow(this.comfyConfig().defaultUpscale)
  );

  protected readonly editAvailable = computed((): boolean =>
    this.comfyConfig().enabled && this.editWorkflow() != null
  );
  protected readonly inpaintAvailable = computed((): boolean =>
    this.comfyConfig().enabled && this.inpaintWorkflow() != null
  );
  protected readonly upscaleAvailable = computed((): boolean =>
    this.comfyConfig().enabled && this.upscaleWorkflow() != null
  );

  protected readonly histOpen = signal(true);
  protected readonly mobileToolOpen = signal(false);
  protected readonly showSaveModal = signal(false);
  protected readonly activeTool = signal<EditorTool>('basis');
  protected readonly compareMode = signal(false);
  protected readonly maskDataUrl = signal<string | null>(null);

  protected readonly maskOverlayRef = viewChild<MaskOverlay>('maskOverlay');

  protected readonly isInpaintMode = computed((): boolean => this.activeTool() === 'inpaint');

  protected readonly cropActive = signal(false);
  protected readonly cropRect = signal<CropRect>({ x: 0, y: 0, w: 100, h: 100 });
  protected readonly cropRatio = signal<CropRatio>('free');

  protected readonly zoomInteractive = computed((): boolean => !this.cropActive());

  protected readonly displayImageUrl = computed((): string =>
    this.currentPreviewUrl() ?? ''
  );

  protected readonly hasSteps = computed((): boolean => this.steps().length > 0);

  ngOnInit(): void {
    if (this.modal()) {
      const kind = this.modalKind();
      const id = this.modalId();
      if (kind != null && id != null) {
        this.store.dispatch(editorActions.init({ kind, id }));
      }
    } else {
      const params = this.route.snapshot.params;
      this.store.dispatch(editorActions.init({
        kind: params['kind'] as EditorTargetKind,
        id: Number(params['id']),
      }));
    }
    this.store.dispatch(modelsActions.loadCapabilities());
    this.store.dispatch(comfyuiActions.loadConfig());
    this.store.dispatch(comfyuiActions.loadWorkflows());
  }

  constructor() {
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
    if (this.modal()) {
      this.closed.emit();
    } else {
      this.router.navigate(['/galerie']);
    }
  }

  protected toggleHist(): void {
    const opening = !this.histOpen();
    this.histOpen.set(opening);
    if (opening) { this.mobileToolOpen.set(false); }
  }

  protected toggleMobileTool(): void {
    const opening = !this.mobileToolOpen();
    this.mobileToolOpen.set(opening);
    if (opening) { this.histOpen.set(false); }
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

  protected setTool(tool: EditorTool): void {
    this.activeTool.set(tool);
    if (tool !== 'inpaint') {
      this.maskDataUrl.set(null);
      this.maskOverlayRef()?.clearMask();
    }
  }

  protected onEdit(event: EditEvent): void {
    this.dispatchGenerative('edit', this.editWorkflow(), {
      prompt: event.prompt,
      resolution: event.resolution,
      maskDataUrl: null,
    });
  }

  protected onInpaint(event: InpaintEvent): void {
    this.dispatchGenerative('inpaint', this.inpaintWorkflow(), {
      prompt: event.prompt.trim().length > 0 ? event.prompt : null,
      resolution: event.resolution,
      maskDataUrl: event.maskDataUrl,
    });
  }

  protected onUpscale(event: UpscaleEvent): void {
    this.dispatchGenerative('upscale', this.upscaleWorkflow(), {
      prompt: null,
      resolution: event.resolution,
      maskDataUrl: null,
    });
  }

  private findDefaultWorkflow(key: string): ComfyUIWorkflow | null {
    if (!key) { return null; }
    return this.activeWorkflows().find((workflow: ComfyUIWorkflow) => workflow.key === key) ?? null;
  }

  private dispatchGenerative(
    task: DefaultRunTask,
    workflow: ComfyUIWorkflow | null,
    run: { prompt: string | null; resolution: EditEvent['resolution']; maskDataUrl: string | null },
  ): void {
    if (workflow == null) { return; }
    const imageSlot = workflow.inputs.find((input) => input.kind === 'image');
    if (imageSlot == null) { return; }
    this.store.dispatch(editorActions.runGenerative({
      task,
      imageSlotKey: imageSlot.key,
      prompt: run.prompt,
      resolution: run.resolution,
      maskDataUrl: run.maskDataUrl,
    }));
  }

  protected onMaskChanged(dataUrl: string | null): void {
    this.maskDataUrl.set(dataUrl);
  }

  protected onClearMask(): void {
    this.maskOverlayRef()?.clearMask();
    this.maskDataUrl.set(null);
  }

  protected onSelectGenerativeResult(): void {
    this.store.dispatch(editorActions.selectGenerativeResult());
  }
}
