import { mapUserDataToEzTreeParams } from './UserDataMapper'
import type { GrowthMetrics } from '../../../types/tree'
import type { StatsNode } from '../../../composables/useStats'
import type { SceneState } from './sceneState'

export class UserDataController {
  private state: SceneState
  private applyOverrides: (overrides: Record<string, any>) => void

  constructor(state: SceneState, applyOverrides: (overrides: Record<string, any>) => void) {
    this.state = state
    this.applyOverrides = applyOverrides
  }

  setUserId(id: string) {
    this.state.userId = id
  }

  /** Compute and store user overrides BEFORE buildScene, so the initial tree
   *  generation uses the correct user-specific parameters (one-shot render). */
  preloadUserOverrides(nodeCount: number, maxDepth: number, userId: string, growth?: GrowthMetrics | null) {
    const widthDepthRatio = maxDepth > 0 ? nodeCount / maxDepth : 1
    this.state.userId = userId
    this.state.lastNodeCount = nodeCount
    this.state.lastMaxDepth = maxDepth
    this.state.lastUserId = userId
    this.state.lastUserOverrides = mapUserDataToEzTreeParams(nodeCount, maxDepth, widthDepthRatio, userId, growth) as any
  }

  updateUserData(statsNodes: StatsNode[], _distribution: Record<string, number>, growth?: GrowthMetrics | null) {
    if (!this.state.ezTree || !this.state.userId) return

    const nodeCount = statsNodes.length
    const maxDepth = statsNodes.reduce((m, n) => Math.max(m, n.depth), 0)
    const widthDepthRatio = maxDepth > 0 ? nodeCount / maxDepth : 1

    const overrides = mapUserDataToEzTreeParams(nodeCount, maxDepth, widthDepthRatio, this.state.userId, growth)

    // Skip if these overrides were already applied by preloadUserOverrides
    if (this.state.lastUserOverrides) {
      const currentKey = `${nodeCount}:${maxDepth}:${this.state.userId}`
      const lastKey = `${this.state.lastNodeCount ?? ''}:${this.state.lastMaxDepth ?? ''}:${this.state.lastUserId ?? ''}`
      if (currentKey === lastKey) return
    }

    this.state.lastNodeCount = nodeCount
    this.state.lastMaxDepth = maxDepth
    this.state.lastUserId = this.state.userId
    this.state.lastUserOverrides = overrides
    this.applyOverrides(overrides)
  }

  /** Debug-only: simulate arbitrary user data to preview tree at different scales.
   *  Does NOT overwrite lastUserOverrides so the "reload real data" button works. */
  simulateUserData(nodeCount: number, maxDepth: number, growthMultiplier: number) {
    if (!this.state.ezTree || !this.state.userId) return
    const widthDepthRatio = maxDepth > 0 ? nodeCount / maxDepth : 1
    const fakeGrowth: GrowthMetrics = {
      avg_stability: 0,
      avg_mastery: 0,
      review_coverage: 0,
      total_nodes: nodeCount,
      reviewed_nodes: 0,
      growth_multiplier: growthMultiplier,
    }
    const overrides = mapUserDataToEzTreeParams(
      nodeCount, maxDepth, widthDepthRatio, this.state.userId, fakeGrowth,
    )
    this.applyOverrides(overrides as any)
  }

  /** Debug-only: re-apply the last REAL user data (undoing simulation). */
  reloadRealUserData() {
    if (!this.state.ezTree || !this.state.lastUserOverrides) return
    this.applyOverrides(this.state.lastUserOverrides)
  }

  /** Cinema demo: rebuild tree geometry at a target growth level. */
  setGrowthLevel(gm: number, nodeCount: number, maxDepth: number) {
    if (!this.state.ezTree) return
    const widthDepthRatio = maxDepth > 0 ? nodeCount / maxDepth : 1
    const fakeGrowth: GrowthMetrics = {
      avg_stability: 0,
      avg_mastery: 0,
      review_coverage: 0,
      total_nodes: nodeCount,
      reviewed_nodes: 0,
      growth_multiplier: gm,
    }
    const overrides = mapUserDataToEzTreeParams(
      nodeCount, maxDepth, widthDepthRatio, this.state.userId || 'demo', fakeGrowth,
    )
    this.applyOverrides(overrides as any)
  }
}
