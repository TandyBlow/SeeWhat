import type { SdfParamEntry } from './sdfParamData';

export const SDF_PARAM_REGISTRY_FOG_BILLBOARD: SdfParamEntry[] = [
  // --- fog (1 entry; uFogColor is derived from skyBottomColor) ---
  {
    name: 'uFogDistance',
    glslType: 'float',
    tsKey: 'bgFogDistance',
    defaultValue: 60.0,
    category: 'fog',
    min: 10,
    max: 200,
    step: 0.5,
    uiLabel: '雾距离',
  },

  // --- billboard (4 entries) ---
  {
    name: 'uBarrelK',
    glslType: 'float',
    tsKey: 'bgBarrelK',
    defaultValue: 0.3,
    category: 'geometry',
    min: 0.0,
    max: 1.0,
    step: 0.05,
    uiLabel: '桶形畸变',
  },
  {
    name: 'uPlatformHeight',
    glslType: 'float',
    tsKey: 'bgPlatformHeight',
    defaultValue: 0.12,
    category: 'geometry',
    min: 0.05,
    max: 0.3,
    step: 0.01,
    uiLabel: 'Billboard高度',
  },
  {
    name: 'uPlatformFade',
    glslType: 'float',
    tsKey: 'bgPlatformFade',
    defaultValue: 0.03,
    category: 'geometry',
    min: 0.005,
    max: 0.1,
    step: 0.005,
    uiLabel: 'Billboard渐隐',
  },
  {
    name: 'uPlatformTexWidth',
    glslType: 'float',
    tsKey: 'bgPlatformTexWidth',
    defaultValue: 1536.0,
    category: 'geometry',
    uiLabel: 'Billboard纹理宽度',
  },
];
