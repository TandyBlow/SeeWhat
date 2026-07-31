import * as THREE from 'three'
import type { TreeStyleParams } from '../../../constants/theme'
import type { SceneState } from './sceneState'

export class LightRig {
  private state: SceneState

  constructor(state: SceneState) {
    this.state = state
  }

  create() {
    const hour = new Date().getHours()
    const lightDir = this.getLightDirection(hour)
    const lightColor = this.getLightColor(hour)

    this.state.mainLight = new THREE.DirectionalLight(lightColor, this.state.currentParams.mainLightIntensity)
    this.state.mainLight.position.copy(lightDir)
    this.state.scene!.add(this.state.mainLight)

    this.state.ambientLight = new THREE.AmbientLight(
      new THREE.Color(...this.state.currentParams.ambientLightColor),
      this.state.currentParams.ambientLightIntensity,
    )
    this.state.scene!.add(this.state.ambientLight)
  }

  private getLightDirection(hour: number): THREE.Vector3 {
    if (hour >= 6 && hour < 12) {
      return new THREE.Vector3(10, 10, 10)
    } else if (hour >= 12 && hour < 18) {
      return new THREE.Vector3(0, 12, 8)
    } else {
      return new THREE.Vector3(-8, 3, 5)
    }
  }

  private getLightColor(hour: number): number {
    if (hour >= 6 && hour < 12) {
      return 0xffe8b0
    } else if (hour >= 12 && hour < 18) {
      return 0xffffff
    } else {
      return 0x8888ff
    }
  }

  applyStyle(params: TreeStyleParams) {
    if (this.state.mainLight) {
      this.state.mainLight.color.set(...params.mainLightColor)
      this.state.mainLight.intensity = params.mainLightIntensity
    }
    if (this.state.ambientLight) {
      this.state.ambientLight.color.set(...params.ambientLightColor)
      this.state.ambientLight.intensity = params.ambientLightIntensity
    }
  }
}
