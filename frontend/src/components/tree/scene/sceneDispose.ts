import * as THREE from 'three'
import type { SceneState, SceneEventListeners } from './sceneState'
import type { AnimationLoop } from './sceneAnimation'
import type { ResizeHandler } from './sceneResize'
import type { BackgroundManager } from './sceneBackground'

export class Disposer {
  private state: SceneState
  private animation: AnimationLoop
  private resize: ResizeHandler
  private background: BackgroundManager
  private listeners: SceneEventListeners

  constructor(state: SceneState, animation: AnimationLoop, resize: ResizeHandler, background: BackgroundManager, listeners: SceneEventListeners) {
    this.state = state
    this.animation = animation
    this.resize = resize
    this.background = background
    this.listeners = listeners
  }

  disposeScene() {
    this.animation.stop()

    this.resize.clearTimer()

    if (this.state.renderer) {
      this.state.renderer.domElement.removeEventListener('click', this.listeners.onClick)
      this.state.renderer.domElement.removeEventListener('webglcontextlost', this.listeners.onContextLost)
      this.state.renderer.domElement.removeEventListener('webglcontextrestored', this.listeners.onContextRestored)
    }

    // Dispose leaf shader material (we own it)
    if (this.state.ezTree?.leavesMesh.material instanceof THREE.ShaderMaterial) {
      this.state.ezTree.leavesMesh.material.dispose()
    }

    // Dispose outline materials
    if (this.state.outlineGroup) {
      for (const child of this.state.outlineGroup.children) {
        if (child instanceof THREE.Mesh && child.material instanceof THREE.Material) {
          child.material.dispose()
        }
      }
      this.state.outlineGroup.clear()
    }

    // Dispose ez-tree (it owns the mesh geometries)
    this.state.ezTree = null

    // Clear group children references (meshes were owned by ez-tree)
    if (this.state.trunkGroup) this.state.trunkGroup.clear()
    if (this.state.leavesGroup) this.state.leavesGroup.clear()

    // Dispose ground (disabled)
    // if (this.groundMesh) {
    //   this.groundMesh.geometry.dispose();
    //   if (this.groundMaterial) {
    //     this.groundMaterial.dispose();
    //     this.groundMaterial = null;
    //   }
    //   this.groundMesh = null;
    // }

    // Dispose particle system (disabled)
    // if (this.particleMesh) {
    //   this.particleMesh.geometry.dispose();
    //   if (this.particleMaterial) {
    //     this.particleMaterial.dispose();
    //     this.particleMaterial = null;
    //   }
    //   this.scene.remove(this.particleMesh);
    //   this.particleMesh = null;
    // }

    // Dispose background
    this.background.dispose()

    if (this.state.renderer) {
      this.state.renderer.dispose()
      if (this.state.renderer.domElement.parentNode === this.state.container) {
        this.state.container.removeChild(this.state.renderer.domElement)
      }
    }

    this.state.contextLost = false
  }
}
