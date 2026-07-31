import { watch, nextTick, type Ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../../stores/authStore'
import { useStyleStore } from '../../stores/styleStore'
import type { TreeStyleParams } from '../../constants/theme'
import type { TreeCanvasScene } from './useTreeCanvasScene'

/**
 * Reactive orchestration for TreeCanvas: every watcher that pushes external
 * state into the scene, plus the two operations only invoked from watchers
 * (applyUserData, onBecameVisible). Call AFTER useTreeCanvasScene.
 */
export function useTreeCanvasSync(scene: TreeCanvasScene, visible: Ref<boolean | undefined>): void {
  const authStore = useAuthStore()
  const styleStore = useStyleStore()
  const { isAuthenticated } = storeToRefs(authStore)

  watch(isAuthenticated, (authed) => {
    if (authed) {
      scene.loadTree()
    } else {
      scene.reset()
    }
  }, { immediate: true })

  async function applyUserData() {
    const userId = authStore.user?.id
    const manager = scene.getManager()
    if (!userId || !manager) return
    manager.setUserId(userId)
    try {
      await scene.fetchStats()
    } catch (e) {
      console.error('[TreeCanvas] fetchStats failed:', e)
      // Stats endpoint may be unavailable; proceed with default tree
      return
    }
    const m = scene.getManager()
    if (m) {
      m.updateUserData(scene.statsNodes.value, styleStore.distribution, scene.getLastSkeleton()?.growth)
    }
  }

  // When user object becomes available (may lag behind isAuthenticated),
  // apply user data to the tree
  watch(() => authStore.user, (user) => {
    if (user?.id && scene.isLoaded()) {
      applyUserData()
    }
  })

  function onBecameVisible() {
    // 不需要重新加载，场景已经存在
    // 只需要确保渲染器正常工作
    scene.getManager()?.handleResize()
  }

  watch(() => styleStore.style, (newStyle) => {
    scene.switchTheme(newStyle, styleStore.backgroundUrl)
  })

  // Apply AI-generated custom params to the 3D tree without touching background
  watch(() => styleStore.styleParams, (newParams) => {
    scene.applyStyleParams(newParams as unknown as TreeStyleParams | undefined)
  })

  // Smooth transition for pending AI-generated style (background preloaded, ready to apply)
  watch(() => styleStore.isPendingReady, (ready) => {
    scene.applyPendingStyle(ready)
  })

  // Update background when AI-generated image URL changes
  watch(() => styleStore.backgroundUrl, (newUrl) => {
    scene.updateBackground(newUrl)
  })

  watch(() => scene.statsNodes.value, () => {
    scene.syncUserData()
  }, { deep: true })

  watch(visible, async (nowVisible, wasVisible) => {
    if (!nowVisible) {
      scene.sceneReady.value = false
      return
    }
    if (wasVisible) return
    await nextTick()
    await new Promise<void>(resolve => requestAnimationFrame(() => resolve()))
    onBecameVisible()
  })
}
