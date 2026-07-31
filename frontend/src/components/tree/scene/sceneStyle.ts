import * as THREE from 'three'
import type { TreeStyleParams } from '../../../constants/theme'
import type { ThemeStyle } from '../../../stores/styleStore'
import type { SceneState } from './sceneState'
import type { LightRig } from './sceneLights'
import type { TreeMaterials } from './sceneMaterials'
import type { BackgroundManager } from './sceneBackground'
import type { LeafTextureManager } from './sceneLeafTextures'

export class StyleController {
  private state: SceneState
  private lights: LightRig
  private materials: TreeMaterials
  private background: BackgroundManager
  private leafTextures: LeafTextureManager

  constructor(state: SceneState, deps: { lights: LightRig; materials: TreeMaterials; background: BackgroundManager; leafTextures: LeafTextureManager }) {
    this.state = state
    this.lights = deps.lights
    this.materials = deps.materials
    this.background = deps.background
    this.leafTextures = deps.leafTextures
  }

  applyStyleParams(params: TreeStyleParams) {
    this.state.currentParams = params

    // Update trunk color
    if (this.state.ezTree?.branchesMesh.material instanceof THREE.MeshToonMaterial) {
      this.state.ezTree.branchesMesh.material.color.set(new THREE.Color(...params.trunkBaseColor))
    }

    // Update leaf shader uniforms
    if (this.state.ezTree?.leavesMesh.material instanceof THREE.ShaderMaterial) {
      const u = this.state.ezTree.leavesMesh.material.uniforms
      u.uBasisColor!.value.set(...params.leafMidColor)
      u.uShadowColor!.value.set(...params.leafDarkColor)
      u.uHighlightColor!.value.set(...params.leafLightColor)
      u.uShadowSize!.value = params.leafShadowSize
      u.uShadowSoftness!.value = params.leafShadowSoftness
      u.uHighlightSize!.value = params.leafHighlightSize
      u.uHighlightSoftness!.value = params.leafHighlightSoftness
      u.uAlphaClipping!.value = params.leafAlphaClipping
      u.uWindStrength!.value = params.windStrength
      u.uWindFrequency!.value = params.windFrequency
      u.uWindScale!.value = params.windScale
    }

    // Swap leaf texture if index changed
    if (params.leafTextureIndex !== this.state.currentLeafTextureIndex) {
      if (this.leafTextures.setIndex(params.leafTextureIndex)) {
        this.materials.setLeafTexture(params.leafTextureIndex)
      }
    }

    // Update ground (disabled)
    // if (this.groundMaterial) {
    //   this.groundMaterial.uniforms.uGroundColor!.value.set(...params.groundColor);
    //   this.groundMaterial.uniforms.uUndulation!.value = params.groundUndulation;
    // }

    // Background is now 2D image, no params to update

    // Update lights
    this.lights.applyStyle(params)

    // Update particle shader uniforms (disabled)
    // if (this.particleMaterial) {
    //   const u = this.particleMaterial.uniforms;
    //   u.uParticleColor!.value.set(...params.particleColor);
    //   u.uParticleShape!.value = params.particleShape;
    //   u.uParticleSpeed!.value = params.particleSpeed;
    //   u.uParticleDirection!.value = params.particleDirection;
    //   u.uParticleSpawnRate!.value = params.particleSpawnRate;
    //   u.uParticleSize!.value = params.particleSize;
    //   u.uWindStrength!.value = params.windStrength;
    //   u.uWindFrequency!.value = params.windFrequency;
    //   u.uWindScale!.value = params.windScale;
    //   if (this.mainLight) {
    //     u.uLightDir!.value.copy(this.mainLight.position).normalize();
    //   }
    // }
  }

  switchTheme(newStyle: ThemeStyle, newBackgroundUrl?: string | null) {
    if (newStyle === this.state.currentStyle && !this.state.themeTransition.isRunning) return
    this.state.currentStyle = newStyle
    this.state.themeTransition.startTransition(newStyle, this.state.currentParams)

    // Update background URL if provided
    if (newBackgroundUrl !== undefined) {
      this.state.backgroundUrl = newBackgroundUrl
    }

    // 切换背景图
    this.background.switchThemeBackground(this.state.backgroundUrl)
  }

  /** Transition to AI-generated custom params with smooth interpolation.
   *  Background URL is deferred until the transition completes. */
  transitionToParams(targetParams: TreeStyleParams, targetStyle: ThemeStyle, newBackgroundUrl?: string | null) {
    this.state.currentStyle = targetStyle
    this.state.themeTransition.startTransition(targetStyle, targetParams)
    if (newBackgroundUrl !== undefined) {
      this.state.pendingBackgroundUrl = newBackgroundUrl
    }
  }

  /** Cinema demo: direct param-to-param transition with custom duration. */
  transitionToParamsDirect(targetParams: TreeStyleParams, durationMs: number) {
    this.state.themeTransition.transitionTo(targetParams, durationMs)
  }

  getCurrentParams(): TreeStyleParams {
    return { ...this.state.currentParams }
  }
}
