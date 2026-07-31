import type { StyleState } from './styleState';
import { getDataAdapter } from './nodeStore';
import { paramsEqual, tryRecoverBgUrl, preloadImage } from './styleParams';
import type { StyleResult } from '../types/node';

export interface StyleCheckActions {
  scheduleCheck(userId: string): void;
  checkAndFetchStyle(userId: string): Promise<void>;
  forceRegenerateStyle(userId: string): Promise<void>;
}

export function createStyleCheckActions(
  state: StyleState,
  waitForStyleGeneration: (userId: string) => Promise<StyleResult | null>,
): StyleCheckActions {
  let checkTimer: ReturnType<typeof setTimeout> | null = null;

  function scheduleCheck(userId: string): void {
    if (checkTimer) clearTimeout(checkTimer);
    checkTimer = setTimeout(() => {
      checkTimer = null;
      checkAndFetchStyle(userId);
    }, 30_000);
  }

  async function checkAndFetchStyle(userId: string): Promise<void> {
    if (state.styleLocked.value) return;
    try {
      const adapter = getDataAdapter();
      await adapter.tagNodes?.(userId);
      const resp = await adapter.fetchStyle?.(userId);
      if (!resp) return;

      // If generation is in progress, poll until it completes
      const data = resp.generating ? await waitForStyleGeneration(userId) : resp;
      if (!data) return;

      // Skip if same as current
      if (data.style === state.style.value && paramsEqual(data.params as Record<string, unknown> | null, state.styleParams.value)) {
        return;
      }

      const newStyle = data.style ?? 'default';

      const bgUrl = data.backgroundUrl ?? null;
      let resolvedBgUrl = bgUrl;

      // Non-default styles require a background image; try disk fallback if missing
      if (newStyle !== 'default') {
        resolvedBgUrl = bgUrl ?? await tryRecoverBgUrl(userId);
        if (!resolvedBgUrl) {
          console.warn(`[styleStore] checkAndFetch: 无背景图URL, 放弃切换. bgUrl=${bgUrl}, bgError="${data.bgError || 'none'}"`);
          return;
        }
        const ok = await preloadImage(resolvedBgUrl);
        if (!ok) {
          console.warn(`[styleStore] checkAndFetch: 背景图预加载失败 url=${resolvedBgUrl}, 放弃切换`);
          return;
        }
      }

      state.pendingParams.value = (data.params as Record<string, unknown>) ?? null;
      state.pendingStyle.value = newStyle;
      state.pendingBackgroundUrl.value = resolvedBgUrl;
      state.isPendingReady.value = true;
    } catch (e) {
      console.warn('[styleStore] checkAndFetch 异常:', e);
    }
  }

  async function forceRegenerateStyle(userId: string): Promise<void> {
    try {
      const adapter = getDataAdapter();
      await adapter.tagNodes?.(userId);
      const resp = await adapter.fetchStyle?.(userId, true);
      if (!resp) return;

      // If another generation is already in progress, wait for it
      const data = resp.generating ? await waitForStyleGeneration(userId) : resp;
      if (!data) return;

      const bgUrl = data.backgroundUrl ?? null;
      const newStyle = data.style ?? 'default';
      let resolvedBgUrl = bgUrl;

      // Non-default styles require a background image; try disk fallback if missing
      if (newStyle !== 'default') {
        resolvedBgUrl = bgUrl ?? await tryRecoverBgUrl(userId);
        if (!resolvedBgUrl) {
          console.warn(`[styleStore] forceRegenerate: 无背景图URL, 放弃. bgUrl=${bgUrl}, bgError="${data.bgError || 'none'}"`);
          return;
        }
        const ok = await preloadImage(resolvedBgUrl);
        if (!ok) {
          console.warn(`[styleStore] forceRegenerate: 背景图预加载失败 url=${resolvedBgUrl}, 放弃`);
          return;
        }
      }

      state.pendingParams.value = (data.params as Record<string, unknown>) ?? null;
      state.pendingStyle.value = newStyle;
      state.pendingBackgroundUrl.value = resolvedBgUrl;
      state.isPendingReady.value = true;
    } catch (e) {
      console.warn('[styleStore] forceRegenerate 异常:', e);
    }
  }

  return { scheduleCheck, checkAndFetchStyle, forceRegenerateStyle };
}
