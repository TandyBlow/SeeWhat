import * as THREE from 'three'
import { outlineVertexShader, outlineFragmentShader } from '../shaders/outline'
import type { SceneState } from './sceneState'

export class OutlineBuilder {
  private state: SceneState

  constructor(state: SceneState) {
    this.state = state
  }

  build() {
    this.state.outlineGroup!.clear()
    const outlineColor = new THREE.Color(...this.state.currentParams.outlineColor)

    // Trunk outline
    if (this.state.ezTree?.branchesMesh) {
      const outlineMat = new THREE.ShaderMaterial({
        vertexShader: outlineVertexShader,
        fragmentShader: outlineFragmentShader,
        uniforms: {
          uOutlineWidth: { value: 0.04 },
          uOutlineColor: { value: outlineColor },
        },
        side: THREE.BackSide,
      })
      const outlineMesh = new THREE.Mesh(this.state.ezTree.branchesMesh.geometry, outlineMat)
      this.state.outlineGroup!.add(outlineMesh)
    }

    // Leaves outline
    if (this.state.ezTree?.leavesMesh) {
      const outlineMat = new THREE.ShaderMaterial({
        vertexShader: outlineVertexShader,
        fragmentShader: outlineFragmentShader,
        uniforms: {
          uOutlineWidth: { value: 0.02 },
          uOutlineColor: { value: outlineColor.clone() },
        },
        side: THREE.BackSide,
      })
      const outlineMesh = new THREE.Mesh(this.state.ezTree.leavesMesh.geometry, outlineMat)
      this.state.outlineGroup!.add(outlineMesh)
    }
  }

  setVisible(visible: boolean) {
    if (this.state.outlineGroup) {
      this.state.outlineGroup.visible = visible
    }
  }
}
