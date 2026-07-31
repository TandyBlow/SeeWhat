import type { StatsNode } from '../../../composables/useStats';
import type { Branch, GrowthMetrics } from '../../../types/tree';
import { Tree as EzTree } from '@dgreenheck/ez-tree';
import { buildCompleteBranch, clamp, hashUUID, lerp } from './userDataGeometry';

type EzTreeOptions = EzTree['options'];

/**
 * Deep-merge `source` into `target`, ADDING keys that don't yet exist in
 * target (unlike ez-tree's built-in `copy()` which skips them).  Mutates and
 * returns `target`.
 */
export function deepMergeOptions(target: Record<string, any>, source: Record<string, any>): Record<string, any> {
  for (const key of Object.keys(source)) {
    const sv = source[key];
    if (sv !== null && typeof sv === 'object' && !Array.isArray(sv)) {
      if (!(key in target) || typeof target[key] !== 'object' || target[key] === null) {
        target[key] = {};
      }
      deepMergeOptions(target[key], sv);
    } else {
      target[key] = sv;
    }
  }
  return target;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export class UserDataMapper {
  private masteryMap = new Map<string, number>();
  private creationDensityMap = new Map<string, number>();
  private globalActivity = 0;

  update(statsNodes: StatsNode[], branches: Branch[], distribution: Record<string, number>) {
    this.masteryMap.clear();
    this.creationDensityMap.clear();

    for (const stat of statsNodes) {
      this.masteryMap.set(stat.id, stat.mastery_score);
    }

    for (const branch of branches) {
      const dist = distribution[branch.node_id] ?? 0;
      this.creationDensityMap.set(branch.node_id, dist);
    }

    const activeCount = statsNodes.filter(n => n.mastery_score > 0).length;
    this.globalActivity = statsNodes.length > 0 ? activeCount / statsNodes.length : 0;
  }

  getMastery(nodeId: string): number {
    return this.masteryMap.get(nodeId) ?? 0;
  }

  getCreationDensity(nodeId: string): number {
    return this.creationDensityMap.get(nodeId) ?? 0;
  }

  getGlobalActivity(): number {
    return this.globalActivity;
  }
}

/**
 * Map user data to ez-tree parameter overrides.
 *
 * Provides a COMPLETE `branch` object (every param for every level), so the
 * preset's branch settings are fully replaced.  Levels is capped at 3
 * (ez-tree's internally-tested limit); the towering-tree effect comes from
 * scaling length / radius / leaf-size through the growth_multiplier
 * (range 0.3 → 2.5).
 *
 * Structure tiers based on nodeCount:
 *   < 20   → levels=2, few children (seedling)
 *   20-80  → levels=3, Oak Medium pattern (sapling)
 *   80-300 → levels=3, Oak Large pattern (mature)
 *   ≥ 300  → levels=3, Oak Large+ with max children (ancient)
 */
export function mapUserDataToEzTreeParams(
  nodeCount: number,
  _maxDepth: number,
  widthDepthRatio: number,
  userId: string,
  growth?: GrowthMetrics | null,
): Partial<EzTreeOptions> {
  const gm = Number.isFinite(growth?.growth_multiplier) ? growth!.growth_multiplier! : 0.5;

  const branch = buildCompleteBranch(nodeCount, gm);

  // Compute terminal count for leaf-index safety check
  const children = (branch as any).children as Record<number, number>;
  const branchLevels = (branch as any).levels as number;
  let terminals = 1;
  const perLevel: number[] = [1];
  for (let lv = 0; lv < branchLevels; lv++) {
    const c = children[lv] ?? 0;
    const next = perLevel[perLevel.length - 1]! * (1 + c);
    perLevel.push(next);
    terminals *= (1 + c);
  }

  // Leaves: count scales with nodeCount and gm, then hard-capped by Uint16Array safety
  const baseLeafCount = clamp(Math.round(nodeCount * 0.4), 4, 35);
  const desiredLeafCount = clamp(Math.round(baseLeafCount * gm), 3, 35);
  // Uint16Array ceiling: each terminal has (1+leafCount) leaves, each leaf = 12 indices (double billboard)
  const maxLeafCount = Math.floor(64900 / (terminals * 12)) - 1;
  const leafCount = Math.min(desiredLeafCount, Math.max(3, maxLeafCount));

  const baseLeafSize = lerp(2.0, 3.5, widthDepthRatio);
  const leafSize = Math.max(1.0, baseLeafSize * gm);

  const seed = hashUUID(userId) % 100000;

  return {
    seed,
    branch: branch as any,
    leaves: {
      count: leafCount,
      size: leafSize,
      sizeVariance: 0.7,
      billboard: 'double',
    } as any,
  };
}
