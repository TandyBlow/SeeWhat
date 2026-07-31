import { SEGMENTS, SECTIONS, TAPER, GNARLINESS, TWIST, ANGLE, START, selectTier } from './userDataTiers';

export function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

export function lerp(a: number, b: number, t: number) {
  return a + (b - a) * clamp(t, 0, 1);
}

export function hashUUID(uuid: string): number {
  let h = 5381;
  for (let i = 0; i < uuid.length; i++) {
    h = ((h << 5) + h + uuid.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

/**
 * Build a complete `branch` options object for ez-tree that covers every
 * parameter for every level (0…levels).  This means the preset's branch
 * settings are fully replaced, avoiding any `undefined` key access.
 */
export function buildCompleteBranch(
  nodeCount: number,
  gm: number,
): Record<string, unknown> {
  const tier = selectTier(nodeCount);
  const levels = tier.levels;

  // Log-interpolate between tier's min/max trunk length
  const t = clamp(Math.log(Math.max(nodeCount, 1)) / Math.log(1000), 0, 1);
  const trunkLen = lerp(tier.trunkLenMin, tier.trunkLenMax, t) * gm;

  // Length falloff: level 1 ≈ 55% of trunk, then ~60% per subsequent level
  const lengthFalloff = [1.0, 0.55, 0.33, 0.20];
  const length: Record<number, number> = {};
  for (let lv = 0; lv <= levels; lv++) {
    length[lv] = Math.max(1.5, trunkLen * lengthFalloff[lv]!);
  }

  // Radius: based on tier.trunkRadius with dampened gm (pow 0.4 so gm=2.5 → only 1.44×)
  const radiusGm = Math.pow(gm, 0.4);
  const radius: Record<number, number> = {};
  const radiusFalloff = [1.0, 0.65, 0.40, 0.25];
  for (let lv = 0; lv <= levels; lv++) {
    radius[lv] = Math.max(0.06, tier.trunkRadius * radiusGm * radiusFalloff[lv]!);
  }

  // Children: use tier defaults, fill missing levels
  const children: Record<number, number> = {};
  for (let lv = 0; lv < levels; lv++) {
    children[lv] = tier.baseChildren[lv] ?? Math.max(2, (tier.baseChildren[lv - 1] ?? 4) - 1);
  }

  // Build full branch spec
  const branch: Record<string, unknown> = { levels };
  const mkLevelObj = (table: Record<number, number>) => {
    const obj: Record<number, number> = {};
    for (let lv = 0; lv <= levels; lv++) obj[lv] = table[lv] ?? table[3] ?? 0;
    return obj;
  };
  const mkLevelObjFrom1 = (table: Record<number, number>) => {
    const obj: Record<number, number> = {};
    for (let lv = 1; lv <= levels; lv++) obj[lv] = table[lv] ?? table[3] ?? 30;
    return obj;
  };

  branch.length = length;
  branch.radius = radius;
  branch.children = children;
  branch.sections = mkLevelObj(SECTIONS);
  branch.segments = mkLevelObj(SEGMENTS);
  branch.taper = mkLevelObj(TAPER);
  branch.gnarliness = mkLevelObj(GNARLINESS);
  branch.twist = mkLevelObj(TWIST);
  branch.angle = mkLevelObjFrom1(ANGLE);
  branch.start = mkLevelObjFrom1(START);

  return branch;
}
