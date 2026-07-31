import { SceneManager } from './scene/SceneManager'
import { useStyleStore, type ThemeStyle } from '../../stores/styleStore'
import type { TreeStyleParams } from '../../constants/theme'
import type { StatsNode } from '../../composables/useStats'
import type { CinemaTreeCanvas } from '../../composables/useCinemaBridge'
import type { GrowthMetrics } from '../../types/tree'

/**
 * Picks the initial style/params/background from the styleStore, honoring a
 * pending AI-generated style (isPendingReady + pendingParams) so the tree
 * renders correctly from frame 1.
 */
export function resolveInitParams(styleStore: ReturnType<typeof useStyleStore>): {
  style: ThemeStyle
  params: TreeStyleParams | null
  bgUrl: string | null
} {
  // If a pending style is ready, use it from the start so the tree
  // renders with the correct visuals instead of default → transition.
  let style: ThemeStyle = styleStore.style
  let params: TreeStyleParams | null =
    styleStore.styleParams as unknown as TreeStyleParams | null
  let bgUrl: string | null = styleStore.backgroundUrl ?? null

  if (styleStore.isPendingReady && styleStore.pendingParams) {
    style = styleStore.pendingStyle as ThemeStyle
    params = styleStore.pendingParams as unknown as TreeStyleParams
    bgUrl = styleStore.pendingBackgroundUrl ?? null
  }

  return { style, params, bgUrl }
}

/**
 * Always preload user overrides when userId is available, even if stats
 * are empty. Using nodeCount=0 maps to tier-0 (seedling) params, which
 * is the correct visual for a new user. This avoids the two-phase flash:
 * default Oak Medium (64u) → seedling (6u) when applyUserData retries.
 */
export function preloadUserOverrides(
  manager: SceneManager,
  statsOk: boolean,
  statsNodes: StatsNode[],
  userId: string,
  growth?: GrowthMetrics | null,
): void {
  const nodeCount = statsOk ? statsNodes.length : 0
  const maxDepth = statsOk
    ? statsNodes.reduce((m, n) => Math.max(m, n.depth), 0)
    : 0
  manager.preloadUserOverrides(nodeCount, maxDepth, userId, growth)
}

/** Builds the CinemaTreeCanvas object assigned to cinemaTreeCanvas.value. */
export function createCinemaBridge(manager: SceneManager): CinemaTreeCanvas {
  return {
    setGrowthLevel: (gm, nodeCount, maxDepth) => manager.setGrowthLevel(gm, nodeCount, maxDepth),
    setTreeGroupScale: (s) => manager.setTreeGroupScale(s),
    transitionToParamsDirect: (params, durationMs) => manager.transitionToParamsDirect(params, durationMs),
    swapBackgroundTexture: (texture) => manager.swapBackgroundTexture(texture),
    getManager: () => manager,
  }
}
