import { ref } from 'vue'
import type * as THREE from 'three'
import type { AuthUser } from '../../types/auth'
import type { NodeContext, TreeNode } from '../../types/node'
import type { SkeletonData } from '../../types/tree'

export type DemoPhase = 'loading' | 'phase1' | 'blackout' | 'phase2' | 'done'

export interface Phase1Scene {
  id: string
  label: string
  accountKey: string
  nodeId?: string | null
  viewState?: string
  durationMs: number
  onEnter?: () => void
}

export interface AccountSnap {
  user: AuthUser
  styleName: string
  styleParams: Record<string, unknown> | null
  bgUrl: string | null
  distribution: Record<string, number>
  treeData: TreeNode[]
  rootContext: NodeContext
  editorNodeId: string
  editorContext: NodeContext
  skeleton: SkeletonData | null
}

export interface DemoStyleEntry {
  index: number
  styleName: string
  params: Record<string, unknown>
  bgPath: string | null
}

/**
 * Shared reactive state + shared mutable session vars for the cinematic demo.
 * Created once in the entry and passed by reference into every demo composable
 * so per-mount semantics match the original <script setup> instance state.
 */
export function useCinematicShared() {
  const demoPhase = ref<DemoPhase>('loading')
  const ready = ref(false)
  const busy = ref(false)
  const paused = ref(false)
  const loadingText = ref('')
  const phase1Scenes = ref<Phase1Scene[]>([])
  const phase1Idx = ref(0)
  const demoStyles = ref<DemoStyleEntry[]>([])

  // Shared mutable objects replacing the original module-level lets
  const cancelled = { value: false }
  const advanceTimer = { value: null as ReturnType<typeof setTimeout> | null }
  const phase2AnimFrame = { value: 0 }

  const snapshots = new Map<string, AccountSnap>()
  const preloadedTextures = new Map<number, THREE.Texture>()

  return {
    demoPhase,
    ready,
    busy,
    paused,
    loadingText,
    phase1Scenes,
    phase1Idx,
    demoStyles,
    cancelled,
    advanceTimer,
    phase2AnimFrame,
    snapshots,
    preloadedTextures,
  }
}

export type CinematicShared = ReturnType<typeof useCinematicShared>
