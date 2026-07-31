import { storeToRefs } from 'pinia'
import { useAuthStore } from '../../stores/authStore'
import { useNodeStore, getDataAdapter } from '../../stores/nodeStore'
import { useStyleStore } from '../../stores/styleStore'
import { usePageTransition } from '../../composables/usePageTransition'
import { presetSkeleton } from '../../composables/useTreeSkeleton'
import * as nodeCache from '../../services/nodeCache'
import type { AuthUser } from '../../types/auth'
import type { SkeletonData } from '../../types/tree'
import type { CinematicShared, AccountSnap } from './useCinematicShared'

const ACCOUNTS: Record<string, { username: string; password: string; editorNodeId: string }> = {
  gamedev: { username: 'alex_gamedev', password: 'demo123', editorNodeId: 'alex_gamedev_关卡设计' },
  fullstack: { username: 'jamie_fullstack', password: 'demo123', editorNodeId: 'jamie_fullstack_RESTful API' },
  piano: { username: 'emma_piano', password: 'demo123', editorNodeId: 'emma_piano_踏板技法' },
  japanese: { username: 'yuki_japanese', password: 'demo123', editorNodeId: 'yuki_japanese_N2语法' },
}

/**
 * Account login/cache/snapshot subsystem plus the shared timing/wait helpers.
 */
export function useCinematicAccounts(shared: CinematicShared) {
  const authStore = useAuthStore()
  const nodeStore = useNodeStore()
  const styleStore = useStyleStore()
  const { isTransitioning } = usePageTransition()
  const { initialized, isAuthenticated } = storeToRefs(authStore)

  function sleep(ms: number) {
    return new Promise<void>(r => setTimeout(r, ms))
  }

  async function waitForSettle(targetViewState: string): Promise<void> {
    const dl = Date.now() + 15000
    while (Date.now() < dl) {
      if (shared.cancelled.value) return
      if (!isTransitioning.value) break
      await sleep(80)
    }
    while (Date.now() < dl) {
      if (shared.cancelled.value) return
      if (nodeStore.viewState === targetViewState) break
      await sleep(80)
    }
    await sleep(700)
  }

  async function waitForStyleLoaded(): Promise<void> {
    const dl = Date.now() + 30000
    while (Date.now() < dl) {
      if (shared.cancelled.value) return
      if (styleStore.loaded) return
      await sleep(200)
    }
  }

  async function captureSnapshot(editorNodeId: string): Promise<AccountSnap> {
    const adapter = getDataAdapter()
    const uid = authStore.user!.id
    const user: AuthUser = { ...authStore.user! }

    const [treeData, styleResp, rootContext, editorContext, skeleton] = await Promise.all([
      adapter.getTree(),
      adapter.fetchStyle?.(uid) ?? Promise.resolve({ style: 'default', distribution: {} } as { style: string; distribution: Record<string, number>; params?: Record<string, unknown>; backgroundUrl?: string | null }),
      adapter.getNodeContext(null),
      adapter.getNodeContext(editorNodeId),
      adapter.fetchTreeSkeleton?.(uid) ?? Promise.resolve(null),
    ])

    return {
      user,
      styleName: styleResp.style ?? 'default',
      styleParams: (styleResp.params as Record<string, unknown>) ?? null,
      bgUrl: styleResp.backgroundUrl ?? null,
      distribution: (styleResp.distribution as Record<string, number>) ?? {},
      treeData,
      rootContext,
      editorNodeId,
      editorContext,
      skeleton: skeleton as SkeletonData | null,
    }
  }

  function injectAccount(snap: AccountSnap) {
    authStore.user = snap.user
    styleStore.forceStyle(snap.styleName, snap.distribution, snap.styleParams ?? undefined, snap.bgUrl)
    nodeStore.treeNodes = snap.treeData
    nodeCache.setCache(null, snap.rootContext)
    nodeCache.setCache(snap.editorNodeId, snap.editorContext)
    if (snap.skeleton) presetSkeleton(snap.skeleton)
  }

  async function loginAs(acct: { username: string; password: string }) {
    if (authStore.user?.username === acct.username) return
    if (isAuthenticated.value) {
      await authStore.logout()
      await sleep(400)
    }
    authStore.mode = 'login'
    authStore.username = acct.username
    authStore.password = acct.password
    await authStore.submitByKnob()
  }

  return {
    ACCOUNTS,
    sleep,
    waitForSettle,
    waitForStyleLoaded,
    captureSnapshot,
    injectAccount,
    loginAs,
    initialized,
    isAuthenticated,
  }
}

export type CinematicAccounts = ReturnType<typeof useCinematicAccounts>
