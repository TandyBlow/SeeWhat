import * as THREE from 'three'
import type { TreeStyleParams } from '../../../constants/theme'
import type { SceneState } from './sceneState'

export class AnimationLoop {
  private state: SceneState
  private applyStyleParams: (params: TreeStyleParams) => void
  private updateBackgroundUrl: (url: string | null) => void

  constructor(state: SceneState, deps: { applyStyleParams: (params: TreeStyleParams) => void; updateBackgroundUrl: (url: string | null) => void }) {
    this.state = state
    this.applyStyleParams = deps.applyStyleParams
    this.updateBackgroundUrl = deps.updateBackgroundUrl
  }

  start() {
    this.state.animationFrameId = requestAnimationFrame(this.renderFrame)
  }

  stop() {
    cancelAnimationFrame(this.state.animationFrameId)
  }

  private renderFrame = () => {
    this.state.animationFrameId = requestAnimationFrame(this.renderFrame)

    if (!this.state.container || this.state.container.offsetParent === null || this.state.contextLost) return

    const now = performance.now() / 1000
    const dt = this.state.lastFrameTime === 0 ? 0.016 : Math.min(now - this.state.lastFrameTime, 0.1)
    this.state.lastFrameTime = now
    this.state.elapsedTime += dt

    // Theme transition
    const transitionParams = this.state.themeTransition.update(performance.now())
    if (transitionParams) {
      this.applyStyleParams(transitionParams)
    }

    // Apply deferred background after transition completes
    if (!this.state.themeTransition.isRunning && this.state.pendingBackgroundUrl !== undefined) {
      this.updateBackgroundUrl(this.state.pendingBackgroundUrl)
      this.state.pendingBackgroundUrl = undefined
    }

    // Background is now 2D image, no time uniform to update

    // Wind sway + time update for custom leaf shader
    if (this.state.ezTree?.leavesMesh.material instanceof THREE.ShaderMaterial) {
      const u = this.state.ezTree.leavesMesh.material.uniforms
      u.uTime!.value = this.state.elapsedTime
      if (this.state.mainLight) {
        u.uLightDir!.value.copy(this.state.mainLight.position).normalize()
      }
    }

    // Update ground time uniform (disabled)
    // if (this.groundMaterial) {
    //   this.groundMaterial.uniforms.uTime!.value = this.elapsedTime;
    // }

    // Update particle time uniform (disabled)
    // if (this.particleMaterial) {
    //   this.particleMaterial.uniforms.uTime!.value = this.elapsedTime;
    // }

    this.state.renderer!.render(this.state.scene!, this.state.camera!)
  }
}
