import * as THREE from 'three'
import type { SkeletonData } from '../../../types/tree'
import type { SceneState, SceneEventListeners } from './sceneState'
import type { BackgroundManager } from './sceneBackground'
import type { LightRig } from './sceneLights'
import type { TreeBuilder } from './sceneTreeBuilder'
import type { CameraRig } from './sceneCamera'
import type { StyleController } from './sceneStyle'
import type { AnimationLoop } from './sceneAnimation'
import type { Disposer } from './sceneDispose'

export class SceneBuilder {
  private state: SceneState
  private background: BackgroundManager
  private lights: LightRig
  private treeBuilder: TreeBuilder
  private cameraRig: CameraRig
  private style: StyleController
  private animation: AnimationLoop
  private disposer: Disposer
  private listeners: SceneEventListeners

  constructor(state: SceneState, deps: {
    background: BackgroundManager
    lights: LightRig
    treeBuilder: TreeBuilder
    cameraRig: CameraRig
    style: StyleController
    animation: AnimationLoop
    disposer: Disposer
    listeners: SceneEventListeners
  }) {
    this.state = state
    this.background = deps.background
    this.lights = deps.lights
    this.treeBuilder = deps.treeBuilder
    this.cameraRig = deps.cameraRig
    this.style = deps.style
    this.animation = deps.animation
    this.disposer = deps.disposer
    this.listeners = deps.listeners
  }

  build(skeleton: SkeletonData) {
    this.state.skeleton = skeleton
    this.disposer.disposeScene()

    this.state.scene = new THREE.Scene()

    this.background.create() // 占位，实际在setupCameraAndRenderer后初始化
    this.lights.create()

    this.state.treeGroup = new THREE.Group()
    this.state.treeGroup.name = 'tree'
    this.state.scene.add(this.state.treeGroup)

    this.state.trunkGroup = new THREE.Group()
    this.state.trunkGroup.name = 'trunk'
    this.state.treeGroup.add(this.state.trunkGroup)

    this.state.leavesGroup = new THREE.Group()
    this.state.leavesGroup.name = 'leaves'
    this.state.treeGroup.add(this.state.leavesGroup)

    this.state.outlineGroup = new THREE.Group()
    this.state.outlineGroup.name = 'outline'
    this.state.outlineGroup.visible = false
    this.state.treeGroup.add(this.state.outlineGroup)

    this.treeBuilder.buildTreeMeshes()
    // this.createGround();
    // this.createParticleMesh();
    this.cameraRig.setup()
    if (!this.state.camera || !this.state.renderer) return

    // 在相机创建后初始化背景
    this.background.init()

    this.state.renderer.domElement.addEventListener('click', this.listeners.onClick)
    this.state.renderer.domElement.addEventListener('webglcontextlost', this.listeners.onContextLost)
    this.state.renderer.domElement.addEventListener('webglcontextrestored', this.listeners.onContextRestored)

    this.style.applyStyleParams(this.state.currentParams)
    this.animation.start()
  }
}
