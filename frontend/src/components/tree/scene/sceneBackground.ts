import * as THREE from 'three'
import { BackgroundPlane } from './BackgroundPlane'
import type { SceneState } from './sceneState'

export class BackgroundManager {
  private state: SceneState

  constructor(state: SceneState) {
    this.state = state
  }

  init() {
    let backgroundPath: string

    if (this.state.backgroundUrl) {
      backgroundPath = this.state.backgroundUrl
    } else {
      if (this.state.currentStyle !== 'default') {
        console.error('[SceneManager] AI背景图不可用，回退到默认背景')
      }
      backgroundPath = '/backgrounds/default.png'
    }

    this.state.backgroundPlane = new BackgroundPlane(backgroundPath, this.state.camera!)
    this.state.scene!.add(this.state.backgroundPlane.getMesh())
  }

  create() {
    // 注意：需要先创建相机才能创建背景
    // 所以这个方法会在 setupCameraAndRenderer 之后被调用
  }

  updateBackgroundUrl(url: string | null) {
    if (url === this.state.backgroundUrl) return
    this.state.backgroundUrl = url
    if (this.state.backgroundPlane && url) {
      this.state.backgroundPlane.updateTexture(url)
    } else if (this.state.backgroundPlane && !url) {
      if (this.state.currentStyle !== 'default') {
        console.error('[SceneManager] AI背景图URL为空，回退到默认背景')
      }
      this.state.backgroundPlane.updateTexture('/backgrounds/default.png')
    }
  }

  switchThemeBackground(url: string | null) {
    this.state.backgroundUrl = url
    if (this.state.backgroundPlane) {
      if (url) {
        this.state.backgroundPlane.updateTexture(url)
      } else {
        if (this.state.currentStyle !== 'default') {
          console.error('[SceneManager] AI背景图不可用，回退到默认背景')
        }
        this.state.backgroundPlane.updateTexture('/backgrounds/default.png')
      }
    }
  }

  updateSize() {
    if (this.state.backgroundPlane) {
      this.state.backgroundPlane.updateSize()
    }
  }

  swapTexture(texture: THREE.Texture) {
    if (this.state.backgroundPlane) {
      this.state.backgroundPlane.swapTexture(texture)
    }
  }

  dispose() {
    if (this.state.backgroundPlane) {
      this.state.backgroundPlane.dispose()
      this.state.backgroundPlane = null
    }
  }
}
