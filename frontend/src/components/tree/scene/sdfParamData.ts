import type { TreeStyleParams } from '../../../constants/theme';
import { SDF_PARAM_REGISTRY_FOG_BILLBOARD } from './sdfParamFogBillboard';

export interface SdfParamEntry {
  name: string;
  glslType: 'vec3' | 'float' | 'int';
  tsKey: keyof TreeStyleParams;
  defaultValue: number | [number, number, number];
  category: 'color' | 'geometry' | 'camera' | 'fog';
  min?: number;
  max?: number;
  step?: number;
  uiLabel?: string;
}

export const SDF_PARAM_REGISTRY_CORE: SdfParamEntry[] = [
  // --- color (3 entries) ---
  {
    name: 'uSkyTopColor',
    glslType: 'vec3',
    tsKey: 'skyTopColor',
    defaultValue: [0.53, 0.81, 0.92],
    category: 'color',
    uiLabel: '天空顶部颜色',
  },
  {
    name: 'uSkyBottomColor',
    glslType: 'vec3',
    tsKey: 'skyBottomColor',
    defaultValue: [0.96, 0.94, 0.92],
    category: 'color',
    uiLabel: '天空底部颜色',
  },
  {
    name: 'uGroundColor',
    glslType: 'vec3',
    tsKey: 'groundColor',
    defaultValue: [0.36, 0.23, 0.12],
    category: 'color',
    uiLabel: '地面颜色',
  },

  // --- camera (4 entries) ---
  {
    name: 'uCamY',
    glslType: 'float',
    tsKey: 'bgCamY',
    defaultValue: 2.8,
    category: 'camera',
    min: 0.5,
    max: 15,
    step: 0.1,
    uiLabel: '相机高度',
  },
  {
    name: 'uCamPitch',
    glslType: 'float',
    tsKey: 'bgCamPitch',
    defaultValue: -0.15,
    category: 'camera',
    min: -0.8,
    max: 0.3,
    step: 0.01,
    uiLabel: '俯视角度',
  },
  {
    name: 'uCamZ',
    glslType: 'float',
    tsKey: 'bgCamZ',
    defaultValue: -6.0,
    category: 'camera',
    min: -20,
    max: -1,
    step: 0.1,
    uiLabel: '相机Z',
  },
  {
    name: 'uFovZoom',
    glslType: 'float',
    tsKey: 'bgFovZoom',
    defaultValue: 1.8,
    category: 'camera',
    min: 0.5,
    max: 5,
    step: 0.05,
    uiLabel: '视场缩放',
  },

  // --- geometry (7 entries) ---
  {
    name: 'uGroundY',
    glslType: 'float',
    tsKey: 'bgGroundY',
    defaultValue: 0.5,
    category: 'geometry',
    min: -5,
    max: 5,
    step: 0.1,
    uiLabel: '地面高度',
  },
  {
    name: 'uHillFreq',
    glslType: 'float',
    tsKey: 'bgHillFreq',
    defaultValue: 0.3,
    category: 'geometry',
    min: 0.05,
    max: 1.0,
    step: 0.01,
    uiLabel: '山丘频率',
  },
  {
    name: 'uHillAmp',
    glslType: 'float',
    tsKey: 'bgHillAmp',
    defaultValue: 5.0,
    category: 'geometry',
    min: 1,
    max: 20,
    step: 0.1,
    uiLabel: '山丘高度',
  },
  {
    name: 'uHillDepth',
    glslType: 'float',
    tsKey: 'bgHillDepth',
    defaultValue: 40.0,
    category: 'geometry',
    min: 10,
    max: 150,
    step: 1,
    uiLabel: '山丘深度',
  },
  {
    name: 'uBldgDepth',
    glslType: 'float',
    tsKey: 'bgBldgDepth',
    defaultValue: 40.0,
    category: 'geometry',
    min: 10,
    max: 150,
    step: 1,
    uiLabel: '建筑深度',
  },
  {
    name: 'uBuildingDensity',
    glslType: 'float',
    tsKey: 'bgBuildingDensity',
    defaultValue: 0.5,
    category: 'geometry',
    min: 0.1,
    max: 1.0,
    step: 0.01,
    uiLabel: '建筑密度',
  },
  {
    name: 'uBuildingHeight',
    glslType: 'float',
    tsKey: 'bgBuildingHeight',
    defaultValue: 4.0,
    category: 'geometry',
    min: 1,
    max: 30,
    step: 0.1,
    uiLabel: '建筑高度',
  },
];

export const SDF_PARAM_REGISTRY: SdfParamEntry[] = [
  ...SDF_PARAM_REGISTRY_CORE,
  ...SDF_PARAM_REGISTRY_FOG_BILLBOARD,
];
