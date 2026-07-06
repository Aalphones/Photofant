import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map } from 'rxjs';
import type { Observable } from 'rxjs';
import type { McpConfig } from '@photofant/models';
import { MCP_CONFIG_DEFAULTS } from '@photofant/models';

interface ConfigResponse {
  data: Record<string, unknown>;
  reboot_required?: boolean | null;
}

interface McpConfigApi {
  enabled: boolean;
  return_images: boolean;
  max_search_results: number;
  thumbnail_size: number;
  require_confirm: boolean;
}

function fromApi(raw: Partial<McpConfigApi> | undefined): McpConfig {
  const block = raw ?? {};
  return {
    enabled:          Boolean(block.enabled          ?? MCP_CONFIG_DEFAULTS.enabled),
    returnImages:     Boolean(block.return_images    ?? MCP_CONFIG_DEFAULTS.returnImages),
    maxSearchResults: Number(block.max_search_results ?? MCP_CONFIG_DEFAULTS.maxSearchResults),
    thumbnailSize:    Number(block.thumbnail_size     ?? MCP_CONFIG_DEFAULTS.thumbnailSize),
    requireConfirm:   Boolean(block.require_confirm   ?? MCP_CONFIG_DEFAULTS.requireConfirm),
  };
}

function toApi(config: McpConfig): McpConfigApi {
  return {
    enabled:            config.enabled,
    return_images:      config.returnImages,
    max_search_results: config.maxSearchResults,
    thumbnail_size:     config.thumbnailSize,
    require_confirm:     config.requireConfirm,
  };
}

/**
 * MCP-Einstellungen leben als ``mcp``-Block in der zentralen settings.json und
 * werden über den generischen ``/api/config``-Endpunkt gelesen/geschrieben — keine
 * eigene Backend-Route nötig (im Gegensatz zur ComfyUI-Integration).
 */
@Injectable({ providedIn: 'root' })
export class McpService {
  private readonly http = inject(HttpClient);

  loadConfig(): Observable<McpConfig> {
    return this.http.get<ConfigResponse>('/api/config').pipe(
      map((response: ConfigResponse) => fromApi(response.data['mcp'] as Partial<McpConfigApi> | undefined)),
    );
  }

  saveConfig(config: McpConfig): Observable<McpConfig> {
    return this.http.patch<ConfigResponse>('/api/config', { data: { mcp: toApi(config) } }).pipe(
      map((response: ConfigResponse) => fromApi(response.data['mcp'] as Partial<McpConfigApi> | undefined)),
    );
  }
}
