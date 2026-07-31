import { ref, computed, inject } from 'vue'
import type { Ref } from 'vue'
import { useDevStore } from '../../stores/devStore'
import { useAuthStore } from '../../stores/authStore'
import { useNodeStore } from '../../stores/nodeStore'
import { useStyleStore } from '../../stores/styleStore'
import { getToken } from '../../utils/api'
import { invalidateSkeleton } from '../../composables/useTreeSkeleton'
import { DEMO_PASSWORD } from './devPanelData'
import type { DemoAccount, ProfileData } from './devPanelData'

export function useDevPanelActions(t: (key: string) => string, locale: Ref<string>) {
  const devStore = useDevStore()
  const authStore = useAuthStore()
  const nodeStore = useNodeStore()
  const styleStore = useStyleStore()

  const isExpanded = ref(false)
  const waitingForScene = ref(false)
  const treeFadeRunning = ref(false)
  const logoutRunning = ref(false)
  const styleRegenRunning = ref(false)
  const resetGrowthRunning = ref(false)
  const profileLoading = ref(false)
  const profileVisible = ref(false)
  const demoSwitchRunning = ref<string | null>(null)
  const profileData = ref<ProfileData | null>(null)

  const currentStyleName = computed(() => styleStore.style || 'default')

  function switchLocale(loc: string) {
    locale.value = loc
    localStorage.setItem('acacia_locale', loc)
  }

  async function onLogout() {
    if (logoutRunning.value) return
    logoutRunning.value = true
    try {
      const ok = await authStore.logout()
      if (ok) {
        nodeStore.resetAfterLogout()
        invalidateSkeleton()
      }
    } finally {
      logoutRunning.value = false
    }
  }

  const triggerTreeFadeTest = inject<() => Promise<void>>('triggerTreeFadeTest', () => Promise.resolve())

  async function onTreeFadeTest() {
    if (treeFadeRunning.value) return
    treeFadeRunning.value = true
    try {
      await triggerTreeFadeTest()
    } finally {
      treeFadeRunning.value = false
    }
  }

  function emitSceneReady() {
    window.dispatchEvent(new CustomEvent('dev-scene-ready'))
    waitingForScene.value = false
  }

  async function onStyleRegen() {
    if (styleRegenRunning.value) return
    const userId = authStore.user?.id
    if (!userId) return
    styleRegenRunning.value = true
    try {
      await styleStore.forceRegenerateStyle(userId)
    } finally {
      styleRegenRunning.value = false
    }
  }

  function onResetStyle() {
    styleStore.resetAndLock()
  }

  function getBackendUrl(): string {
    return import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:7860'
  }

  async function onResetGrowth() {
    if (resetGrowthRunning.value) return
    resetGrowthRunning.value = true
    try {
      const token = getToken()
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers.Authorization = `Bearer ${token}`
      const url = `${getBackendUrl()}/daily-quiz/reset`
      const res = await fetch(url, { method: 'POST', headers })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error((data as any).detail ?? t('dev.resetFailed'))
      }
      await nodeStore.checkDailyQuizStatus()
    } catch (e: unknown) {
      console.error('重置今日成长状态失败:', e)
    } finally {
      resetGrowthRunning.value = false
    }
  }

  async function onShowProfileText() {
    if (profileLoading.value) return
    profileLoading.value = true
    try {
      const token = getToken()
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token) headers.Authorization = `Bearer ${token}`
      const url = `${getBackendUrl()}/debug/profile-text`
      const res = await fetch(url, { headers })
      if (!res.ok) throw new Error('Failed to fetch profile text')
      profileData.value = await res.json()
      profileVisible.value = true
    } catch (e: unknown) {
      console.error('获取知识画像失败:', e)
    } finally {
      profileLoading.value = false
    }
  }

  async function onSwitchDemoAccount(acct: DemoAccount) {
    if (demoSwitchRunning.value) return
    demoSwitchRunning.value = acct.username
    try {
      if (authStore.isAuthenticated) {
        await authStore.logout()
        nodeStore.resetAfterLogout()
        invalidateSkeleton()
        await new Promise(r => setTimeout(r, 500))
      }
      authStore.mode = 'login'
      authStore.username = acct.username
      authStore.password = DEMO_PASSWORD
      const ok = await authStore.submitByKnob()
      if (ok) {
        const uid = authStore.user?.id
        if (uid) {
          await styleStore.fetchStyle(uid)
        }
      }
    } catch (e: unknown) {
      console.error('切换演示账号失败:', e)
    } finally {
      demoSwitchRunning.value = null
    }
  }

  function onWaitingForScene() {
    if (devStore.manualSceneReady) {
      waitingForScene.value = true
    }
  }

  return {
    isExpanded,
    waitingForScene,
    treeFadeRunning,
    logoutRunning,
    styleRegenRunning,
    resetGrowthRunning,
    profileLoading,
    profileVisible,
    demoSwitchRunning,
    profileData,
    currentStyleName,
    switchLocale,
    onLogout,
    onTreeFadeTest,
    emitSceneReady,
    onStyleRegen,
    onResetStyle,
    onResetGrowth,
    onShowProfileText,
    onSwitchDemoAccount,
    onWaitingForScene,
  }
}
