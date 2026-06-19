export interface AppInfo {
  version: string;
  python_version: string;
  db_path: string;
  db_size_bytes: number;
  cache_db_path: string;
  cache_db_size_bytes: number;
  onnx_version: string;
  last_migration: string | null;
  gpu_name: string | null;
  vram_gb: number | null;
  cuda_version: string | null;
  env_flags: Record<string, string>;
}
