import { provide, nextTick, watch } from 'vue'
import { useOfficialTransition } from './useOfficialTransition'
import { usePageTransition } from './usePageTransition'
import { applyDisplayedState } from './mainLayoutContentContext'
import { CONTENT_SINK_MS, CONTENT_SLIDE_MS, sleep } from './useMainLayoutState'
import type { MainLayoutContentCtx } from './mainLayoutContentContext'

/**
 * Small-layout official knowledge-point click orchestration.
 * Sink → non-clicked slide left (clicked stays) → clicked slides down to
 * anchor → content slides in from right → rise.
 */
export function useMainLayoutOfficial(ctx: MainLayoutContentCtx): void {
  const { state } = ctx
  const {
    phase: otPhase,
    animating: otAnimating,
    animToken: otAnimToken,
    anchorItemId,
    clickedItemId,
    anchorDeltaY,
    anchorPrep,
    hideNonAnchorItems,
    anchorItemAction,
  } = useOfficialTransition()
  const { isTransitioning } = usePageTransition()

  async function startSmallLayoutOfficialTransition(item: { id: string; name: string; action?: () => void }, rowEl: HTMLElement): Promise<void> {
    // Cancel existing official animation
    if (otAnimating.value) {
      otAnimToken.value++
      otPhase.value = 'idle'
      otAnimating.value = false
      hideNonAnchorItems.value = false
      anchorItemId.value = null
      clickedItemId.value = null
      anchorDeltaY.value = 0
      anchorPrep.value = false
      anchorItemAction.value = null
    }

    // Cancel any in-flight content animation
    if (state.contentAnimating.value) {
      state.contentAnimToken.value++
      state.contentPhase.value = 'idle'
      state.contentAnimating.value = false
    }

    otAnimating.value = true
    state.contentAnimating.value = true
    const token = ++otAnimToken.value
    anchorItemAction.value = item.action ?? null
    clickedItemId.value = item.id

    // ---- Phase 1: SINK (240ms) ----
    otPhase.value = 'sinking'
    await nextTick()
    await sleep(CONTENT_SINK_MS)
    if (token !== otAnimToken.value) return

    // ---- Measurement: capture clicked row position before it moves ----
    const rowRect = rowEl.getBoundingClientRect()

    // ---- Phase 2: NAV SLIDE (280ms) — non-clicked rows slide left, clicked stays ----
    otPhase.value = 'sliding'
    await sleep(CONTENT_SLIDE_MS)
    if (token !== otAnimToken.value) return

    // ---- DOM swap: show anchor, change viewState ----
    anchorItemId.value = item.id
    hideNonAnchorItems.value = true

    // Fire the action to change viewState (starts async startTransition)
    const action = anchorItemAction.value
    if (action) {
      action()
    }

    // Wait for startTransition to finish — it sets content display to '' asynchronously
    if (isTransitioning.value) {
      await new Promise<void>(resolve => {
        const stop = watch(isTransitioning, (v) => {
          if (!v) { stop(); resolve() }
        })
      })
    }
    await nextTick()
    if (token !== otAnimToken.value) return

    // Keep content hidden during anchor slide so it doesn't block the animation.
    // startTransition re-enabled it; we override that until the anchor finishes sliding.
    const contentEl = state.contentAreaRef.value
    if (contentEl) contentEl.style.display = 'none'

    // Measure anchor final position
    const anchorEl = document.querySelector('.anchor-official-shell') as HTMLElement | null
    const anchorRect = anchorEl?.getBoundingClientRect()
    if (anchorRect) {
      anchorDeltaY.value = anchorRect.top - rowRect.top
    }

    // Set anchor in prep position (at clicked item's original location, invisible)
    anchorPrep.value = true
    await nextTick()
    void document.body.offsetHeight // force reflow

    // ---- Phase 3: ANCHOR SLIDE DOWN (280ms) ----
    anchorPrep.value = false
    otPhase.value = 'anchor-sliding'

    // Wait for anchor slide transition to complete
    await new Promise<void>((resolve) => {
      const shell = document.querySelector('.anchor-official-shell') as HTMLElement | null
      if (!shell) { resolve(); return }
      const onEnd = (e: TransitionEvent) => {
        if (e.propertyName === 'transform') {
          shell.removeEventListener('transitionend', onEnd)
          resolve()
        }
      }
      shell.addEventListener('transitionend', onEnd)
      setTimeout(() => {
        shell.removeEventListener('transitionend', onEnd)
        resolve()
      }, CONTENT_SLIDE_MS + 80)
    })
    if (token !== otAnimToken.value) return

    // ---- Phase 4: CONTENT SLIDE IN (280ms) ----
    applyDisplayedState(ctx)
    state.contentPhase.value = 'slide-in-prep'

    await nextTick()
    if (token !== otAnimToken.value) return

    // Show content — wrapper is at prep position (off-screen right, opacity 0)
    if (contentEl) contentEl.style.display = ''

    // Force reflow, then trigger slide-in
    const reflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
    void reflowEl?.offsetHeight
    state.contentPhase.value = 'slide-in'
    await sleep(CONTENT_SLIDE_MS)
    if (token !== otAnimToken.value) return

    // ---- Cleanup ----
    otPhase.value = 'idle'
    state.contentPhase.value = 'idle'
    otAnimating.value = false
    state.contentAnimating.value = false
    anchorDeltaY.value = 0
    anchorPrep.value = false
    anchorItemAction.value = null
    clickedItemId.value = null
    // anchorItemId and hideNonAnchorItems stay set — anchor remains visible
    // during the special state so the user can click it to return.
  }

  provide('startSmallLayoutOfficialTransition', startSmallLayoutOfficialTransition)
}
