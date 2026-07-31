import * as THREE from 'three'
import type { SceneState } from './sceneState'

import leafTex1Url from '../../../assets/textures/TreeLeaves01.png'
import leafTex2Url from '../../../assets/textures/TreeLeaves02.png'
import leafTex3Url from '../../../assets/textures/TreeLeaves03.png'

export class LeafTextureManager {
  private state: SceneState

  constructor(state: SceneState) {
    this.state = state
    this.loadLeafTextures()
  }

  private loadLeafTextures() {
    const loader = new THREE.TextureLoader()
    const urls = [leafTex1Url, leafTex2Url, leafTex3Url]
    for (const url of urls) {
      const tex = loader.load(url)
      tex.premultiplyAlpha = true
      tex.colorSpace = THREE.SRGBColorSpace
      this.state.leafTextures.push(tex)
    }
  }

  get currentTexture(): THREE.Texture | undefined {
    return this.state.leafTextures[this.state.currentLeafTextureIndex] || this.state.leafTextures[0]
  }

  setIndex(index: number): boolean {
    if (index < 0 || index >= this.state.leafTextures.length) return false
    this.state.currentLeafTextureIndex = index
    return true
  }
}
