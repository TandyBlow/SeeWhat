import type { Scene, OrthographicCamera, WebGLRenderer, Group, Box3, DirectionalLight, AmbientLight, Texture } from 'three'
import { Vector3 } from 'three'
import type { SkeletonData } from '../../../types/tree'
import type { TreeStyleParams } from '../../../constants/theme'
import { THEME_DEFAULT } from '../../../constants/theme'
import type { ThemeStyle } from '../../../stores/styleStore'
import { ThemeTransition } from './ThemeTransition'
import type { BackgroundPlane } from './BackgroundPlane'
import type { Tree as EzTree } from '@dgreenheck/ez-tree'

export type EzTreeOptions = EzTree['options']

export interface SceneManagerCallbacks {
  onResizeStart: () => void
  onResizeEnd: () => void
  onBranchClick: (nodeId: string) => void
}

export interface SceneEventListeners {
  onClick: (e: MouseEvent) => void
  onContextLost: (e: Event) => void
  onContextRestored: () => void
}

export interface SceneState {
  scene: Scene | null
  camera: OrthographicCamera | null
  renderer: WebGLRenderer | null
  treeGroup: Group | null
  trunkGroup: Group | null
  leavesGroup: Group | null
  outlineGroup: Group | null
  backgroundPlane: BackgroundPlane | null
  backgroundUrl: string | null
  pendingBackgroundUrl: string | null | undefined
  mainLight: DirectionalLight | null
  ambientLight: AmbientLight | null
  ezTree: EzTree | null
  leafTextures: Texture[]
  currentLeafTextureIndex: number
  themeTransition: ThemeTransition
  lastFrameTime: number
  elapsedTime: number
  container: HTMLElement
  skeleton: SkeletonData | null
  currentStyle: ThemeStyle
  currentParams: TreeStyleParams
  animationFrameId: number
  callbacks: SceneManagerCallbacks
  userId: string
  lastUserOverrides: Partial<EzTreeOptions> | null
  lastNodeCount: number | null
  lastMaxDepth: number | null
  lastUserId: string | null
  treeBounds: Box3 | null
  treeCenter: Vector3
  isResizing: boolean
  resizeDebounceTimer: number | null
  refContainerW: number
  refContainerH: number
  lastContainerW: number
  lastContainerH: number
  contextLost: boolean
}

export function createSceneState(
  container: HTMLElement,
  initialStyle: ThemeStyle,
  callbacks: SceneManagerCallbacks,
  customParams?: TreeStyleParams | null,
  backgroundUrl?: string | null,
): SceneState {
  const base: TreeStyleParams = { ...THEME_DEFAULT }
  return {
    scene: null,
    camera: null,
    renderer: null,
    treeGroup: null,
    trunkGroup: null,
    leavesGroup: null,
    outlineGroup: null,
    backgroundPlane: null,
    backgroundUrl: backgroundUrl ?? null,
    pendingBackgroundUrl: undefined,
    mainLight: null,
    ambientLight: null,
    ezTree: null,
    leafTextures: [],
    currentLeafTextureIndex: 0,
    themeTransition: new ThemeTransition(initialStyle, customParams),
    lastFrameTime: 0,
    elapsedTime: 0,
    container,
    skeleton: null,
    currentStyle: initialStyle,
    currentParams: customParams ? ({ ...base, ...customParams } as TreeStyleParams) : base,
    animationFrameId: 0,
    callbacks,
    userId: '',
    lastUserOverrides: null,
    lastNodeCount: null,
    lastMaxDepth: null,
    lastUserId: null,
    treeBounds: null,
    treeCenter: new Vector3(),
    isResizing: false,
    resizeDebounceTimer: null,
    refContainerW: 0,
    refContainerH: 0,
    lastContainerW: 0,
    lastContainerH: 0,
    contextLost: false,
  }
}
