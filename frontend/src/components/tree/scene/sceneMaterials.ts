import * as THREE from 'three'
import { crownVertexShader, crownFragmentShader } from '../shaders/crown'
import type { SceneState } from './sceneState'

export class TreeMaterials {
  private state: SceneState

  constructor(state: SceneState) {
    this.state = state
  }

  applyCustomMaterials() {
    if (!this.state.ezTree) return
    const params = this.state.currentParams

    // Override trunk material with MeshToonMaterial
    if (this.state.ezTree.branchesMesh.material instanceof THREE.Material) {
      this.state.ezTree.branchesMesh.material.dispose()
    }
    this.state.ezTree.branchesMesh.material = new THREE.MeshToonMaterial({
      color: new THREE.Color(...params.trunkBaseColor),
    })

    // Override leaf material with custom soft toon shader + alpha mask texture
    if (this.state.ezTree.leavesMesh.material instanceof THREE.Material) {
      this.state.ezTree.leavesMesh.material.dispose()
    }
    const leafTex = this.state.leafTextures[this.state.currentLeafTextureIndex] || this.state.leafTextures[0]
    const lightDir = this.state.mainLight
      ? this.state.mainLight.position.clone().normalize()
      : new THREE.Vector3(0.5, 0.8, 0.3)

    this.state.ezTree.leavesMesh.material = new THREE.ShaderMaterial({
      vertexShader: crownVertexShader,
      fragmentShader: crownFragmentShader,
      uniforms: {
        uBasisColor: { value: new THREE.Color(...params.leafMidColor) },
        uShadowColor: { value: new THREE.Color(...params.leafDarkColor) },
        uHighlightColor: { value: new THREE.Color(...params.leafLightColor) },
        uAlphaMask: { value: leafTex },
        uAlphaClipping: { value: params.leafAlphaClipping },
        uShadowSize: { value: params.leafShadowSize },
        uShadowSoftness: { value: params.leafShadowSoftness },
        uHighlightSize: { value: params.leafHighlightSize },
        uHighlightSoftness: { value: params.leafHighlightSoftness },
        uLightDir: { value: lightDir },
        uTime: { value: 0 },
        uWindStrength: { value: params.windStrength },
        uWindFrequency: { value: params.windFrequency },
        uWindScale: { value: params.windScale },
      },
      side: THREE.DoubleSide,
      transparent: true,
    })
  }

  setLeafTexture(index: number) {
    this.state.currentLeafTextureIndex = index
    if (this.state.ezTree?.leavesMesh.material instanceof THREE.ShaderMaterial) {
      this.state.ezTree.leavesMesh.material.uniforms.uAlphaMask!.value = this.state.leafTextures[index]
    }
  }
}
