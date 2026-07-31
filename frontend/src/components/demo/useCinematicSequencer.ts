import { useNodeStore } from '../../stores/nodeStore'
import type { CinematicShared } from './useCinematicShared'
import type { CinematicAccounts } from './useCinematicAccounts'
import type { CinematicPhase2 } from './useCinematicPhase2'

/**
 * Phase 1 scene sequencing: auto-advance timer, pause/prev/next/jump controls,
 * and the blackout transition into Phase 2.
 */
export function useCinematicSequencer(shared: CinematicShared, accounts: CinematicAccounts, phase2: CinematicPhase2) {
  const nodeStore = useNodeStore()

  async function advancePhase1Scene(idx: number) {
    if (shared.busy.value || shared.cancelled.value) return
    shared.busy.value = true
    clearAdvanceTimer()

    const scene = shared.phase1Scenes.value[idx]
    if (!scene) { shared.busy.value = false; return }

    const prevScene = shared.phase1Scenes.value[shared.phase1Idx.value]

    if (!prevScene || prevScene.accountKey !== scene.accountKey) {
      const snap = shared.snapshots.get(scene.accountKey)
      if (snap) accounts.injectAccount(snap)
    }

    if (scene.viewState) {
      nodeStore.setViewState(scene.viewState as any)
      await accounts.waitForSettle(scene.viewState)
    } else {
      nodeStore.loadNode(scene.nodeId ?? null)
      await accounts.waitForSettle('display')
    }

    scene.onEnter?.()

    shared.phase1Idx.value = idx
    if (!shared.cancelled.value) {
      shared.busy.value = false
      schedulePhase1Advance()
    }
  }

  function clearAdvanceTimer() {
    if (shared.advanceTimer.value) { clearTimeout(shared.advanceTimer.value); shared.advanceTimer.value = null }
  }

  function schedulePhase1Advance() {
    clearAdvanceTimer()
    if (shared.paused.value || shared.cancelled.value) return
    const s = shared.phase1Scenes.value[shared.phase1Idx.value]
    if (!s) return
    shared.advanceTimer.value = setTimeout(async () => {
      if (shared.paused.value || shared.cancelled.value) return
      const next = shared.phase1Idx.value + 1
      if (next >= shared.phase1Scenes.value.length) {
        // All Phase 1 scenes done → transition to Phase 2
        transitionToPhase2()
      } else {
        await advancePhase1Scene(next)
      }
    }, s.durationMs)
  }

  function togglePause() {
    shared.paused.value = !shared.paused.value
    if (shared.paused.value) clearAdvanceTimer()
    else schedulePhase1Advance()
  }

  async function nextScene() { await advancePhase1Scene((shared.phase1Idx.value + 1) % shared.phase1Scenes.value.length) }
  async function prevScene() { await advancePhase1Scene((shared.phase1Idx.value - 1 + shared.phase1Scenes.value.length) % shared.phase1Scenes.value.length) }
  async function jumpToPhase1Scene(i: number) { if (i !== shared.phase1Idx.value && !shared.busy.value) await advancePhase1Scene(i) }

  async function transitionToPhase2() {
    shared.demoPhase.value = 'blackout'
    await accounts.sleep(400)
    shared.demoPhase.value = 'phase2'
    phase2.runPhase2()
  }

  return { clearAdvanceTimer, schedulePhase1Advance, togglePause, nextScene, prevScene, jumpToPhase1Scene, transitionToPhase2 }
}

export type CinematicSequencer = ReturnType<typeof useCinematicSequencer>
