import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  PLATFORM_ID,
  signal,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { Icon } from '@photofant/ui';
import { mcpActions, mcpSelectors } from '@photofant/store';
import type { McpConfig } from '@photofant/models';

@Component({
  selector: 'pf-einstellungen-mcp',
  imports: [Icon],
  templateUrl: './mcp.html',
  styleUrl: './mcp.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class McpSection {
  private readonly store = inject(Store);
  private readonly isBrowser = isPlatformBrowser(inject(PLATFORM_ID));

  readonly config = this.store.selectSignal(mcpSelectors.selectConfig);
  readonly isSaving = this.store.selectSignal(mcpSelectors.selectIsSaving);
  readonly error = this.store.selectSignal(mcpSelectors.selectError);

  readonly draftEnabled = signal<boolean>(false);
  readonly draftReturnImages = signal<boolean>(true);
  readonly draftMaxSearchResults = signal<number>(50);
  readonly draftThumbnailSize = signal<number>(256);
  readonly draftRequireConfirm = signal<boolean>(true);

  /** Rückmeldung „kopiert!" pro Codeblock — schlichter Timeout-Reset. */
  readonly copiedKey = signal<string | null>(null);

  readonly isDirty = computed((): boolean => {
    const cfg = this.config();
    return (
      this.draftEnabled() !== cfg.enabled ||
      this.draftReturnImages() !== cfg.returnImages ||
      this.draftMaxSearchResults() !== cfg.maxSearchResults ||
      this.draftThumbnailSize() !== cfg.thumbnailSize ||
      this.draftRequireConfirm() !== cfg.requireConfirm
    );
  });

  /** Basis-URL der laufenden App (in der Produktion identisch mit dem Backend-Port). */
  readonly connectionUrl = computed((): string => {
    const origin = this.isBrowser ? window.location.origin : 'http://127.0.0.1:8000';
    return `${origin}/mcp`;
  });

  /** Fertiger MCP-Client-Config-Block (Streamable-HTTP, Default). */
  readonly clientConfigUrl = computed((): string =>
    JSON.stringify(
      { mcpServers: { photofant: { url: this.connectionUrl() } } },
      null,
      2,
    )
  );

  /** Alternative für stdio-only Clients (ältere Claude-Desktop-Stände) via mcp-remote-Bridge. */
  readonly clientConfigBridge = computed((): string =>
    JSON.stringify(
      { mcpServers: { photofant: { command: 'npx', args: ['mcp-remote', this.connectionUrl()] } } },
      null,
      2,
    )
  );

  constructor() {
    effect(() => {
      this.store.dispatch(mcpActions.loadConfig());
    });
    effect(() => {
      const cfg = this.config();
      this.draftEnabled.set(cfg.enabled);
      this.draftReturnImages.set(cfg.returnImages);
      this.draftMaxSearchResults.set(cfg.maxSearchResults);
      this.draftThumbnailSize.set(cfg.thumbnailSize);
      this.draftRequireConfirm.set(cfg.requireConfirm);
    });
  }

  toggleEnabled(): void {
    this.draftEnabled.update((value: boolean) => !value);
  }

  toggleReturnImages(): void {
    this.draftReturnImages.update((value: boolean) => !value);
  }

  toggleRequireConfirm(): void {
    this.draftRequireConfirm.update((value: boolean) => !value);
  }

  onMaxSearchResultsChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(500, Math.max(1, isNaN(raw) ? 50 : raw));
    target.value = String(clamped);
    this.draftMaxSearchResults.set(clamped);
  }

  onThumbnailSizeChange(target: HTMLInputElement): void {
    const raw = parseInt(target.value, 10);
    const clamped = Math.min(1024, Math.max(64, isNaN(raw) ? 256 : raw));
    target.value = String(clamped);
    this.draftThumbnailSize.set(clamped);
  }

  save(): void {
    const config: McpConfig = {
      enabled: this.draftEnabled(),
      returnImages: this.draftReturnImages(),
      maxSearchResults: this.draftMaxSearchResults(),
      thumbnailSize: this.draftThumbnailSize(),
      requireConfirm: this.draftRequireConfirm(),
    };
    this.store.dispatch(mcpActions.saveConfig({ config }));
  }

  copy(key: string, text: string): void {
    if (!this.isBrowser || !navigator.clipboard) {
      return;
    }
    navigator.clipboard.writeText(text).then(() => {
      this.copiedKey.set(key);
      setTimeout(() => this.copiedKey.set(null), 1500);
    });
  }
}
