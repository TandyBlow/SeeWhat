import { i18n } from '../i18n';
import type { DataAdapter } from '../types/node';

let dataAdapter: DataAdapter | null = null;

export function setDataAdapter(adapter: DataAdapter): void {
  dataAdapter = adapter;
}

export function getDataAdapter(): DataAdapter {
  if (!dataAdapter) throw new Error('Data adapter not initialized');
  return dataAdapter;
}

export function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return i18n.global.t('errors.unknown');
}

export function clearAdapterCache(): void {
  dataAdapter?.clearCache?.();
}
