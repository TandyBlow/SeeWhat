// ---------------------------------------------------------------------------
// Pre-built branch parameter tables (synthesised from Oak Small/Medium/Large
// presets + extrapolation).  Each key is a level index.  Levels 0-3 match the
// Oak Medium preset roughly; levels 4-5 are conservative extrapolations.
// ---------------------------------------------------------------------------

/** Number of radial segments per level. Higher = rounder branch cross-section. */
export const SEGMENTS: Record<number, number> = { 0: 8, 1: 6, 2: 5, 3: 4 };

/** Number of length-wise sections per level. */
export const SECTIONS: Record<number, number> = { 0: 10, 1: 8, 2: 6, 3: 4 };

/** Branch taper per level (0 = no taper, 1 = tapers to point). */
export const TAPER: Record<number, number> = { 0: 0.73, 1: 0.55, 2: 0.6, 3: 0.7 };

/** Gnarliness (random perturbation) per level. */
export const GNARLINESS: Record<number, number> = { 0: 0.05, 1: 0.1, 2: 0.15, 3: 0.08 };

/** Twist per level. */
export const TWIST: Record<number, number> = { 0: 0, 1: 0.05, 2: 0, 3: 0 };

/** Angle of child branches relative to parent (degrees). */
export const ANGLE: Record<number, number> = { 1: 55, 2: 50, 3: 40 };

/** Where child branches start on the parent (0-1 along length). */
export const START: Record<number, number> = { 1: 0.4, 2: 0.3, 3: 0.25 };

// ---------------------------------------------------------------------------
// Tier-based defaults (length, radius, children) — scaled by NodeCount
// ---------------------------------------------------------------------------

export interface BranchTier {
  levels: number;
  /** Trunk length (level 0) at gm=1.0, scaled by nodeCount log interpolation. */
  trunkLenMin: number;
  trunkLenMax: number;
  /** Trunk radius at gm=1.0. */
  trunkRadius: number;
  /** Children per parent level. Keys 0..levels-1. */
  baseChildren: Record<number, number>;
}

const TIERS: BranchTier[] = [
  // Tier 0: seedling (nodeCount < 20) — compact, 2-level structure
  { levels: 2, trunkLenMin: 10, trunkLenMax: 20, trunkRadius: 0.6, baseChildren: { 0: 4, 1: 3 } },
  // Tier 1: sapling (20-80) — terminals=105, safe
  { levels: 3, trunkLenMin: 20, trunkLenMax: 32, trunkRadius: 0.9, baseChildren: { 0: 6, 1: 4, 2: 2 } },
  // Tier 2: mature (80-300) — terminals=144, safe
  { levels: 3, trunkLenMin: 28, trunkLenMax: 42, trunkRadius: 1.3, baseChildren: { 0: 7, 1: 5, 2: 2 } },
  // Tier 3: ancient (300+) — terminals=192, leafCount auto-capped at 27
  { levels: 3, trunkLenMin: 40, trunkLenMax: 60, trunkRadius: 1.8, baseChildren: { 0: 7, 1: 5, 2: 3 } },
];

export function selectTier(nodeCount: number): BranchTier {
  if (nodeCount < 20) return TIERS[0]!;
  if (nodeCount < 80) return TIERS[1]!;
  if (nodeCount < 300) return TIERS[2]!;
  return TIERS[3]!;
}
