import type { Ref } from 'vue'
import { useStyleStore, type ThemeStyle } from '../../stores/styleStore'
import type { TreeStyleParams } from '../../constants/theme'
import type { SceneManager } from './scene/SceneManager'
import type { SkeletonData } from '../../types/tree'
import type { StatsNode } from '../../composables/useStats'

export interface SceneControlsDeps {
  getManager: () => SceneManager | null
  getLastSkeleton: () => SkeletonData | null
  statsNodes: Ref<StatsNode[]>
  styleStore: ReturnType<typeof useStyleStore>
}

/**
 * Imperative control helpers for the TreeCanvas scene. Each method looks up
 * the live manager via getManager(), so a null manager (post-cleanup) is a
 * safe no-op.
 */
export function createSceneControls(deps: SceneControlsDeps) {
  const { getManager, getLastSkeleton, statsNodes, styleStore } = deps

  function syncUserData() {
    const manager = getManager()
    if (manager) {
      manager.updateUserData(statsNodes.value, styleStore.distribution, getLastSkeleton()?.growth)
    }
  }

  function switchTheme(newStyle: ThemeStyle, bgUrl?: string | null) {
    const manager = getManager()
    if (manager) {
      manager.switchTheme(newStyle, bgUrl)
    }
  }

  function applyStyleParams(params?: TreeStyleParams | null) {
    const manager = getManager()
    if (manager && params?.leafMidColor) {
      manager.applyStyleParamsPublic(params)
    }
  }

  function applyPendingStyle(ready: boolean) {
    const manager = getManager()
    if (!ready || !manager || !styleStore.pendingParams) return
    const targetParams = styleStore.pendingParams as unknown as TreeStyleParams
    const targetStyle = styleStore.pendingStyle
    const bgUrl = styleStore.pendingBackgroundUrl
    manager.transitionToParams(targetParams, targetStyle, bgUrl ?? null)
    // Apply pending after transition completes (800ms duration + 100ms buffer)
    setTimeout(() => {
      styleStore.applyPendingStyle()
    }, 900)
  }

  function updateBackground(newUrl: string | null) {
    const manager = getManager()
    if (manager) {
      manager.updateBackgroundUrl(newUrl ?? null)
    }
  }

  function setGrowthLevel(gm: number, nodeCount: number, maxDepth: number): void {
    getManager()?.setGrowthLevel(gm, nodeCount, maxDepth)
  }

  function setTreeGroupScale(s: number): void {
    getManager()?.setTreeGroupScale(s)
  }

  function transitionToParamsDirect(params: any, durationMs: number): void {
    getManager()?.transitionToParamsDirect(params, durationMs)
  }

  function swapBackgroundTexture(texture: any): void {
    getManager()?.swapBackgroundTexture(texture)
  }

  return {
    syncUserData,
    switchTheme,
    applyStyleParams,
    applyPendingStyle,
    updateBackground,
    setGrowthLevel,
    setTreeGroupScale,
    transitionToParamsDirect,
    swapBackgroundTexture,
  }
}
