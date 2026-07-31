import { useI18n } from 'vue-i18n'
import { useNodeStore } from '../../stores/nodeStore'
import type { CinematicShared } from './useCinematicShared'
import type { CinematicAccounts } from './useCinematicAccounts'
import type { CinematicPhase2 } from './useCinematicPhase2'
import type { CinematicSequencer } from './useCinematicSequencer'

/**
 * The start() boot orchestration, invoked synchronously inside the composable
 * during setup to mirror the original 'start()' call at the end of the script.
 */
export function useCinematicInit(shared: CinematicShared, accounts: CinematicAccounts, phase2: CinematicPhase2, sequencer: CinematicSequencer) {
  const nodeStore = useNodeStore()
  const { t } = useI18n()

  async function start() {
    shared.cancelled.value = false

    shared.loadingText.value = t('demo.initializing')
    while (!accounts.initialized.value) {
      if (shared.cancelled.value) return
      await accounts.sleep(100)
    }

    // Step 1: login as gamedev, let MainLayout fully initialize
    shared.loadingText.value = t('demo.loggingIn')
    await accounts.loginAs(accounts.ACCOUNTS.gamedev!)
    await accounts.waitForStyleLoaded()
    await accounts.sleep(3000)
    shared.snapshots.set('gamedev', await accounts.captureSnapshot(accounts.ACCOUNTS.gamedev!.editorNodeId))

    // Step 2: prefetch remaining accounts + load demo styles in parallel
    shared.loadingText.value = t('demo.preloading')
    const prefetchTasks = ['fullstack', 'piano', 'japanese'].map(async (key) => {
      if (shared.cancelled.value) return
      const acct = accounts.ACCOUNTS[key]!
      await accounts.loginAs(acct)
      await accounts.waitForStyleLoaded()
      await accounts.sleep(2000)
      shared.snapshots.set(key, await accounts.captureSnapshot(acct.editorNodeId))
    })

    await Promise.all([...prefetchTasks, phase2.loadDemoStyles()])

    // Preload background textures after styles are loaded
    if (shared.demoStyles.value.length > 0) {
      shared.loadingText.value = t('demo.preloadingBg')
      phase2.preloadBackgroundTextures()
      // Give textures a moment to start loading
      await accounts.sleep(500)
    }

    // Step 3: inject gamedev back so demo starts with gamedev tree
    shared.loadingText.value = t('demo.preparingPlayback')
    const gamedevSnap = shared.snapshots.get('gamedev')!
    accounts.injectAccount(gamedevSnap)
    nodeStore.loadNode(null)
    await accounts.waitForSettle('display')

    // Step 4: build Phase 1 scene list
    const EDITOR_NODE = accounts.ACCOUNTS.gamedev!.editorNodeId
    shared.phase1Scenes.value = [
      { id: 'editor',    label: t('demo.sceneNodeDetail'),   accountKey: 'gamedev',   nodeId: EDITOR_NODE, durationMs: 2800 },
      { id: 'chat',      label: t('demo.sceneChat'),     accountKey: 'gamedev',   nodeId: EDITOR_NODE, durationMs: 2500,
        onEnter: () => window.dispatchEvent(new CustomEvent('cinema:chat-mode')) },
      { id: 'dailyquiz', label: t('demo.sceneDailyQuiz'),     accountKey: 'gamedev',   viewState: 'daily_quiz', durationMs: 2500 },
      { id: 'overview',  label: t('demo.sceneTreeOverview'),   accountKey: 'gamedev',   viewState: 'tree_overview', durationMs: 2500 },
      { id: 'tree',      label: t('demo.sceneHome'),     accountKey: 'gamedev',   nodeId: null, durationMs: 2000 },
    ]

    // Step 5: start Phase 1
    shared.demoPhase.value = 'phase1'
    shared.ready.value = true

    sequencer.schedulePhase1Advance()
  }

  start()
}

export type CinematicInit = ReturnType<typeof useCinematicInit>
