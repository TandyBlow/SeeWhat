import type { StyleState, ThemeStyle } from './styleState';
import { getDataAdapter } from './nodeStore';
import { applyThemeToDOM, applyParamsToDOM, resetParamsToDOM } from './styleDom';
import { tryRecoverBgUrl, preloadImage } from './styleParams';
import type { StyleResult } from '../types/node';

export interface StyleActions {
  applyTheme(): void;
  applyThemeFromParams(params: Record<string, unknown>): void;
  fetchStyle(userId: string): Promise<void>;
  forceStyle(s: ThemeStyle, dist?: Record<string, number>, params?: Record<string, unknown>, bgUrl?: string | null): void;
  reset(): void;
  resetAndLock(): void;
  applyPendingStyle(): void;
}

export function createStyleActions(
  state: StyleState,
  waitForStyleGeneration: (userId: string) => Promise<StyleResult | null>,
): StyleActions {
  function applyTheme(): void {
    applyThemeToDOM(state.style.value, state.styleParams.value);
  }

  function applyThemeFromParams(params: Record<string, unknown>): void {
    applyParamsToDOM(params);
  }

  async function fetchStyle(userId: string): Promise<void> {
    try {
      const adapter = getDataAdapter();
      await adapter.tagNodes?.(userId);
      const resp = await adapter.fetchStyle?.(userId);
      if (!resp) {
        console.warn('[styleStore] fetchStyle — 后端返回空响应');
        return;
      }

      // If generation is in progress, poll until it completes
      const data = resp.generating ? await waitForStyleGeneration(userId) : resp;
      if (!data) return;

      const bgUrl = data.backgroundUrl ?? null;
      const newStyle = data.style ?? 'default';

      if (newStyle !== 'default') {
        // Non-default styles go through the pending mechanism so the tree
        // transitions smoothly (no abrupt texture swap / CSS gradient change).
        const resolvedBgUrl = bgUrl ?? await tryRecoverBgUrl(userId);
        if (!resolvedBgUrl) {
          console.warn(`[styleStore] 初始加载: 无背景图URL, 保持default风格. bgUrl=${bgUrl}, bgError="${data.bgError || 'none'}", 磁盘恢复也失败`);
        } else {
          const ok = await preloadImage(resolvedBgUrl);
          if (!ok) {
            console.warn(`[styleStore] 初始加载: 背景图预加载失败 url=${resolvedBgUrl}, 保持default风格`);
          } else {
            state.pendingParams.value = (data.params as Record<string, unknown>) ?? null;
            state.pendingStyle.value = newStyle;
            state.pendingBackgroundUrl.value = resolvedBgUrl;
            state.distribution.value = data.distribution ?? {};
            state.isPendingReady.value = true;
          }
        }
      } else {
        // Default style can be applied directly — no background to preload.
        state.backgroundUrl.value = bgUrl;
        state.styleParams.value = (data.params as Record<string, unknown>) ?? null;
        state.distribution.value = data.distribution ?? {};
        state.style.value = newStyle;
      }
    } catch (e) {
      console.warn('[styleStore] fetchStyle 异常:', e);
    } finally {
      state.loaded.value = true;
      // Only apply DOM theme if the style was set directly (default or
      // already-committed pending). Pending styles will apply theme via
      // applyPendingStyle() when the tree transition completes.
      if (state.style.value !== 'default' && state.styleParams.value) {
        applyTheme();
      } else {
        resetParamsToDOM();
      }
    }
  }

  function forceStyle(s: ThemeStyle, dist?: Record<string, number>, params?: Record<string, unknown>, bgUrl?: string | null): void {
    state.style.value = s;
    if (dist) state.distribution.value = dist;
    if (params) state.styleParams.value = params;
    if (bgUrl !== undefined) state.backgroundUrl.value = bgUrl;
    state.loaded.value = true;
    applyTheme();
  }

  function reset(): void {
    state.style.value = 'default';
    state.styleParams.value = null;
    state.backgroundUrl.value = null;
    state.distribution.value = {};
    state.loaded.value = false;
    applyTheme();
  }

  function resetAndLock(): void {
    state.styleLocked.value = true;
    reset();
  }

  function applyPendingStyle(): void {
    state.style.value = state.pendingStyle.value;
    state.styleParams.value = state.pendingParams.value;
    state.backgroundUrl.value = state.pendingBackgroundUrl.value;
    state.distribution.value = {};

    state.pendingParams.value = null;
    state.pendingStyle.value = 'default';
    state.pendingBackgroundUrl.value = null;
    state.isPendingReady.value = false;

    state.loaded.value = true;
    applyTheme();
  }

  return { applyTheme, applyThemeFromParams, fetchStyle, forceStyle, reset, resetAndLock, applyPendingStyle };
}
