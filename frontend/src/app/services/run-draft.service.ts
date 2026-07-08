import { DestroyRef, inject, Injectable, NgZone, signal } from '@angular/core';

/** Der geteilte Run-Entwurf: alles, was über Tabs hinweg zusammengesammelt wird. */
export interface RunDraftSnapshot {
  workflowId: string | null;
  slotBindings: Record<string, number | number[]>;
  faceSlotBindings: Record<string, number | number[]>;
  versionSlotBindings: Record<string, number | number[]>;
  toggleBindings: Record<string, boolean>;
  batchAxisKey: string | null;
}

/** Ergebnis eines Batch-Binds — signalisiert der UI, ob die Batch-Achse verschoben wurde (Toast-Hinweis). */
export interface BatchBindResult {
  batchAxisShifted: boolean;
}

const STORAGE_KEY = 'photofant.run-draft';
const CHANNEL_NAME = 'photofant-run-draft';

function emptyDraft(): RunDraftSnapshot {
  return {
    workflowId: null,
    slotBindings: {},
    faceSlotBindings: {},
    versionSlotBindings: {},
    toggleBindings: {},
    batchAxisKey: null,
  };
}

/**
 * Hält den Run-Leisten-Entwurf zentral und synchronisiert ihn live über alle Browser-Tabs
 * derselben App: jede Änderung landet in `localStorage` (überlebt Neustart) und wird per
 * `BroadcastChannel` an die anderen Tabs geschickt. So kann man Slot 1 in einem Tab und Slot 2
 * in einem anderen füllen — der Entwurf ist überall derselbe. Der „scharfe" Slot bleibt bewusst
 * lokal in der jeweiligen Galerie-Komponente; nur die tatsächlichen Belegungen sind geteilt.
 */
@Injectable({ providedIn: 'root' })
export class RunDraftService {
  private readonly zone = inject(NgZone);
  private readonly destroyRef = inject(DestroyRef);

  readonly workflowId          = signal<string | null>(null);
  readonly slotBindings        = signal<Record<string, number | number[]>>({});
  readonly faceSlotBindings    = signal<Record<string, number | number[]>>({});
  readonly versionSlotBindings = signal<Record<string, number | number[]>>({});
  readonly toggleBindings      = signal<Record<string, boolean>>({});
  readonly batchAxisKey        = signal<string | null>(null);

  // BroadcastChannel fehlt in Test-/SSR-Umgebungen — dort läuft der Service rein lokal weiter.
  private readonly channel: BroadcastChannel | null =
    typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel(CHANNEL_NAME);

  constructor() {
    this.hydrateFromStorage();
    if (this.channel !== null) {
      // onmessage feuert außerhalb der Angular-Zone → run() sorgt für Change Detection.
      this.channel.onmessage = (event: MessageEvent<RunDraftSnapshot>): void => {
        this.zone.run((): void => this.applyIncoming(event.data));
      };
      this.destroyRef.onDestroy((): void => this.channel?.close());
    }
  }

  /** Workflow wählen (oder abwählen) — leert den Entwurf, da die Slots workflow-spezifisch sind. */
  setWorkflow(workflowId: string | null): void {
    this.setSignals({ ...emptyDraft(), workflowId });
    this.persistAndBroadcast();
  }

  /** Einzelbild in einen Slot binden. Ein evtl. dort gebundenes Gesicht wird überschrieben. */
  bindAsset(slotKey: string, assetId: number): void {
    this.clearFaceBinding(slotKey);
    if (this.batchAxisKey() === slotKey) { this.batchAxisKey.set(null); }
    this.slotBindings.set({ ...this.slotBindings(), [slotKey]: assetId });
    this.persistAndBroadcast();
  }

  /** Gesicht in einen Slot binden. Eine evtl. dort gebundene Asset-Belegung wird überschrieben. */
  bindFace(slotKey: string, faceId: number): void {
    this.clearAssetBinding(slotKey);
    if (this.batchAxisKey() === slotKey) { this.batchAxisKey.set(null); }
    this.faceSlotBindings.set({ ...this.faceSlotBindings(), [slotKey]: faceId });
    this.persistAndBroadcast();
  }

  /** Asset zum Batch-Array eines Slots hinzufügen (Strg+Klick). Nur ein Slot darf Batch-Achse sein. */
  batchBindAsset(slotKey: string, assetId: number): BatchBindResult {
    this.clearFaceBinding(slotKey);

    const currentBindings = this.slotBindings();
    const existing = currentBindings[slotKey];
    const existingArray = Array.isArray(existing)
      ? existing
      : existing != null ? [existing] : [];

    if (existingArray.includes(assetId)) {
      this.persistAndBroadcast();
      return { batchAxisShifted: false };
    }

    const updatedArray = [...existingArray, assetId];
    const previousBatchKey = this.batchAxisKey();
    let batchAxisShifted = false;

    if (previousBatchKey !== null && previousBatchKey !== slotKey) {
      // Alter Batch-Slot fällt auf sein erstes Element zurück — nur ein Slot trägt die Achse.
      const oldBatch = currentBindings[previousBatchKey];
      const oldFirst = Array.isArray(oldBatch) ? oldBatch[0] : oldBatch;
      this.slotBindings.set({
        ...currentBindings,
        [previousBatchKey]: oldFirst ?? 0,
        [slotKey]: updatedArray,
      });
      batchAxisShifted = true;
    } else {
      this.slotBindings.set({ ...currentBindings, [slotKey]: updatedArray });
    }
    this.batchAxisKey.set(slotKey);
    this.persistAndBroadcast();
    return { batchAxisShifted };
  }

  /** Einen Workflow-Toggle setzen. */
  setToggle(key: string, value: boolean): void {
    this.toggleBindings.update((current: Record<string, boolean>) => ({ ...current, [key]: value }));
    this.persistAndBroadcast();
  }

  /** Entwurf komplett leeren (bewusste Aktion — nicht beim Zuklappen der Run-Leiste). */
  clear(): void {
    this.setSignals(emptyDraft());
    this.persistAndBroadcast();
  }

  /** Ob überhaupt etwas gebunden ist — für die „Workflow wechseln?"-Rückfrage. */
  hasBindings(): boolean {
    return Object.keys(this.slotBindings()).length > 0
      || Object.keys(this.faceSlotBindings()).length > 0
      || Object.keys(this.versionSlotBindings()).length > 0;
  }

  private clearFaceBinding(slotKey: string): void {
    const faceBindings = { ...this.faceSlotBindings() };
    delete faceBindings[slotKey];
    this.faceSlotBindings.set(faceBindings);
  }

  private clearAssetBinding(slotKey: string): void {
    const assetBindings = { ...this.slotBindings() };
    delete assetBindings[slotKey];
    this.slotBindings.set(assetBindings);
  }

  private snapshot(): RunDraftSnapshot {
    return {
      workflowId:          this.workflowId(),
      slotBindings:        this.slotBindings(),
      faceSlotBindings:    this.faceSlotBindings(),
      versionSlotBindings: this.versionSlotBindings(),
      toggleBindings:      this.toggleBindings(),
      batchAxisKey:        this.batchAxisKey(),
    };
  }

  private setSignals(draft: RunDraftSnapshot): void {
    this.workflowId.set(draft.workflowId);
    this.slotBindings.set(draft.slotBindings);
    this.faceSlotBindings.set(draft.faceSlotBindings);
    this.versionSlotBindings.set(draft.versionSlotBindings);
    this.toggleBindings.set(draft.toggleBindings);
    this.batchAxisKey.set(draft.batchAxisKey);
  }

  /** Eingehende Änderung aus einem anderen Tab: Signale setzen + localStorage angleichen, NICHT zurücksenden. */
  private applyIncoming(draft: RunDraftSnapshot): void {
    this.setSignals(draft);
    this.writeStorage(draft);
  }

  private persistAndBroadcast(): void {
    const draft = this.snapshot();
    this.writeStorage(draft);
    this.channel?.postMessage(draft);
  }

  private writeStorage(draft: RunDraftSnapshot): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(draft));
    } catch {
      // localStorage nicht verfügbar (privater Modus/Quota) — Sync läuft dann nur über den Channel.
    }
  }

  private hydrateFromStorage(): void {
    let raw: string | null = null;
    try {
      raw = localStorage.getItem(STORAGE_KEY);
    } catch {
      return;
    }
    if (raw === null) { return; }
    try {
      const parsed = JSON.parse(raw) as Partial<RunDraftSnapshot>;
      this.setSignals({ ...emptyDraft(), ...parsed });
    } catch {
      // Kaputter Eintrag — ignorieren und mit leerem Entwurf starten.
    }
  }
}
