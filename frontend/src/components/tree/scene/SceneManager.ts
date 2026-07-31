import * as THREE from 'three'
import type { SkeletonData, GrowthMetrics } from '../../../types/tree'
import type { StatsNode } from '../../../composables/useStats'
import type { TreeStyleParams } from '../../../constants/theme'
import type { ThemeStyle } from '../../../stores/styleStore'
import { createSceneState } from './sceneState'
import type { SceneState, SceneManagerCallbacks, EzTreeOptions } from './sceneState'
import { LeafTextureManager } from './sceneLeafTextures'
import { CameraRig } from './sceneCamera'
import { LightRig } from './sceneLights'
import { TreeMaterials } from './sceneMaterials'
import { OutlineBuilder } from './sceneOutlines'
import { TreeBuilder } from './sceneTreeBuilder'
import { BackgroundManager } from './sceneBackground'
import { StyleController } from './sceneStyle'
import { UserDataController } from './sceneUserData'
import { AnimationLoop } from './sceneAnimation'
import { ResizeHandler } from './sceneResize'
import { Disposer } from './sceneDispose'
import { SceneBuilder } from './sceneBuilder'

export type { SceneManagerCallbacks } from './sceneState'

export class SceneManager {
  private state: SceneState
  private leafTextures: LeafTextureManager
  private materials: TreeMaterials
  private outlines: OutlineBuilder
  private treeBuilder: TreeBuilder
  private background: BackgroundManager
  private style: StyleController
  private userData: UserDataController
  private resize: ResizeHandler
  private disposer: Disposer
  private builder: SceneBuilder

  private onCanvasClick = (_event: MouseEvent) => {}

  private onContextLost = (event: Event) => {
    event.preventDefault()
    this.state.contextLost = true
  }

  private onContextRestored = () => {
    this.state.contextLost = false
    if (this.state.skeleton) {
      this.rebuildScene()
    }
  }

  constructor(container: HTMLElement, initialStyle: ThemeStyle, callbacks: SceneManagerCallbacks, customParams?: TreeStyleParams | null, backgroundUrl?: string | null) {
    this.state = createSceneState(container, initialStyle, callbacks, customParams, backgroundUrl)
    this.leafTextures = new LeafTextureManager(this.state)
    const cameraRig = new CameraRig(this.state)
    const lights = new LightRig(this.state)
    this.materials = new TreeMaterials(this.state)
    this.outlines = new OutlineBuilder(this.state)
    this.treeBuilder = new TreeBuilder(this.state, cameraRig, this.materials, this.outlines)
    this.background = new BackgroundManager(this.state)
    this.style = new StyleController(this.state, { lights, materials: this.materials, background: this.background, leafTextures: this.leafTextures })
    this.userData = new UserDataController(this.state, (overrides) => this.treeBuilder.applyOverrides(overrides))
    const animation = new AnimationLoop(this.state, {
      applyStyleParams: (params) => this.style.applyStyleParams(params),
      updateBackgroundUrl: (url) => this.background.updateBackgroundUrl(url),
    })
    this.resize = new ResizeHandler(this.state, cameraRig, this.background)
    const listeners = {
      onClick: this.onCanvasClick,
      onContextLost: this.onContextLost,
      onContextRestored: this.onContextRestored,
    }
    this.disposer = new Disposer(this.state, animation, this.resize, this.background, listeners)
    this.builder = new SceneBuilder(this.state, {
      background: this.background,
      lights,
      treeBuilder: this.treeBuilder,
      cameraRig,
      style: this.style,
      animation,
      disposer: this.disposer,
      listeners,
    })
  }

  buildScene(skeleton: SkeletonData) {
    this.builder.build(skeleton)
  }

  switchTheme(newStyle: ThemeStyle, newBackgroundUrl?: string | null) {
    this.style.switchTheme(newStyle, newBackgroundUrl)
  }

  updateBackgroundUrl(url: string | null) {
    this.background.updateBackgroundUrl(url)
  }
  transitionToParams(targetParams: TreeStyleParams, targetStyle: ThemeStyle, newBackgroundUrl?: string | null) {
    this.style.transitionToParams(targetParams, targetStyle, newBackgroundUrl)
  }
  setUserId(id: string) {
    this.userData.setUserId(id)
  }
  preloadUserOverrides(nodeCount: number, maxDepth: number, userId: string, growth?: GrowthMetrics | null) {
    this.userData.preloadUserOverrides(nodeCount, maxDepth, userId, growth)
  }
  updateUserData(statsNodes: StatsNode[], _distribution: Record<string, number>, growth?: GrowthMetrics | null) {
    this.userData.updateUserData(statsNodes, _distribution, growth)
  }
  handleResize() {
    this.resize.handleResize()
  }

  async rebuildScene() {
    if (!this.state.skeleton) return
    this.disposer.disposeScene()
    this.buildScene(this.state.skeleton)
  }

  setLeafTexture(index: number) {
    if (this.leafTextures.setIndex(index)) {
      this.materials.setLeafTexture(index)
    }
  }

  dispose() {
    this.disposer.disposeScene()
  }

  // --- Debug API ---

  getCurrentParams(): TreeStyleParams {
    return this.style.getCurrentParams()
  }
  getEzTreeOptions(): EzTreeOptions | null {
    return this.state.ezTree ? this.state.ezTree.options : null
  }
  setEzTreeOptions(options: EzTreeOptions) {
    if (!this.state.ezTree) return
    this.treeBuilder.applyOverrides(options as any)
  }
  loadEzTreePreset(presetName: string) {
    if (!this.state.ezTree) return
    this.state.ezTree.loadPreset(presetName)
    this.treeBuilder.rebuildTreeGroups()
  }
  setMainLightPos(x: number, y: number, z: number) {
    if (this.state.mainLight) {
      this.state.mainLight.position.set(x, y, z)
    }
  }
  setTrunkVisible(visible: boolean) {
    if (this.state.trunkGroup) {
      this.state.trunkGroup.visible = visible
    }
  }
  applyStyleParamsPublic(params: TreeStyleParams) {
    this.style.applyStyleParams(params)
  }
  simulateUserData(nodeCount: number, maxDepth: number, growthMultiplier: number) {
    this.userData.simulateUserData(nodeCount, maxDepth, growthMultiplier)
  }
  reloadRealUserData() {
    this.userData.reloadRealUserData()
  }
  setGrowthLevel(gm: number, nodeCount: number, maxDepth: number) {
    this.userData.setGrowthLevel(gm, nodeCount, maxDepth)
  }
  setTreeGroupScale(s: number) {
    if (this.state.treeGroup) {
      this.state.treeGroup.scale.set(s, s, s)
    }
  }
  transitionToParamsDirect(targetParams: TreeStyleParams, durationMs: number) {
    this.style.transitionToParamsDirect(targetParams, durationMs)
  }
  swapBackgroundTexture(texture: THREE.Texture) {
    this.background.swapTexture(texture)
  }
  getTreeGroup(): THREE.Group | null {
    return this.state.treeGroup as THREE.Group | null
  }
  setOutlineVisible(visible: boolean) {
    this.outlines.setVisible(visible)
  }
}
