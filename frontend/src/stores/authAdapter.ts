import { i18n } from '../i18n';
import type { AuthAdapter } from '../types/auth';

let authAdapter: AuthAdapter | null = null;

export function setAuthAdapter(adapter: AuthAdapter): void {
  authAdapter = adapter;
}

export function getAuthAdapter(): AuthAdapter | null {
  return authAdapter;
}

export function formatAuthError(error: unknown): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return i18n.global.t('errors.authFailed');
}
