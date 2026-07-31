import * as THREE from 'three';
import type { TreeStyleParams } from '../../../constants/theme';
import { SDF_PARAM_REGISTRY } from './sdfParamData';

/** Generate GLSL uniform declarations from the registry. */
export function generateGlslUniforms(): string {
  return SDF_PARAM_REGISTRY.map((entry) => {
    const comment = entry.glslType === 'vec3' ? ' // rgb' : '';
    return `uniform ${entry.glslType} ${entry.name};${comment}`;
  }).join('\n');
}

/** Create a Three.js uniforms object from registry defaults. */
export function createUniforms(): Record<string, THREE.IUniform> {
  const uniforms: Record<string, THREE.IUniform> = {};
  for (const entry of SDF_PARAM_REGISTRY) {
    if (entry.glslType === 'vec3') {
      const color = entry.defaultValue as [number, number, number];
      uniforms[entry.name] = { value: new THREE.Color(color[0], color[1], color[2]) };
    } else if (entry.glslType === 'int') {
      uniforms[entry.name] = { value: entry.defaultValue as number };
    } else {
      uniforms[entry.name] = { value: entry.defaultValue as number };
    }
  }
  return uniforms;
}

/** Apply TreeStyleParams values to existing uniforms (no allocation per frame). */
export function applyParamsToUniforms(
  uniforms: Record<string, THREE.IUniform>,
  params: TreeStyleParams,
): void {
  for (const entry of SDF_PARAM_REGISTRY) {
    const val = params[entry.tsKey];
    if (entry.glslType === 'vec3') {
      const color = val as [number, number, number];
      (uniforms[entry.name]!.value as THREE.Color).set(color[0], color[1], color[2]);
    } else if (entry.glslType === 'int') {
      uniforms[entry.name]!.value = Math.round(val as number);
    } else {
      uniforms[entry.name]!.value = val as number;
    }
  }
}
