import { nextTick, watch } from 'vue'
import { applyDisplayedState } from './mainLayoutContentContext'
import { CONTENT_SINK_MS, CONTENT_SLIDE_MS, CONTENT_RISE_MS, TREE_MASK_FADE_MS, sleep } from './useMainLayoutState'
import type { MainLayoutContentCtx } from './mainLayoutContentContext'

export interface MainLayoutEntrance {
  playEntranceAnimation: (token: number) => Promise<boolean>
  playInitialAnimation: () => Promise<void>
  handleLoginTransition: () => Promise<void>
}

/**
 * Coordinated entrance/login animation trio. Receives the shared ctx.
 */
export function useMainLayoutEntrance(ctx: MainLayoutContentCtx): MainLayoutEntrance {
  const { state } = ctx

  // Shared entrance animation: sliding + rising for all areas.
  // Prerequisites: contentPhase='slide-in-prep' and entrancePhase='prep' must
  // already be set. display refs must already point to the target content.
  async function playEntranceAnimation(token: number): Promise<boolean> {
    const willShowTree = ctx.display.showTree.value

    if (willShowTree) {
      state.treeOverlayActive.value = true
      const maskEl = state.treeMaskRef.value
      if (maskEl) maskEl.style.transition = 'none'
      state.treeMaskVisible.value = true

      await nextTick()
      if (token !== state.contentAnimToken.value) return false
      const reflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
      void reflowEl?.offsetHeight
      if (maskEl) maskEl.style.transition = ''

      state.contentPhase.value = 'tree-mask'
      state.entrancePhase.value = 'sliding'

      await nextTick()
      await ctx.waitForSceneReady(token)
      if (token !== state.contentAnimToken.value) return false
      state.treeMaskVisible.value = false
      await sleep(TREE_MASK_FADE_MS)
      if (token !== state.contentAnimToken.value) return false
    } else {
      const reflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
      void reflowEl?.offsetHeight
      state.contentPhase.value = 'slide-in'
      state.entrancePhase.value = 'sliding'
      await sleep(CONTENT_SLIDE_MS)
      if (token !== state.contentAnimToken.value) return false
    }

    if (!state.displayedSkipContentGlass.value) {
      state.contentPhase.value = 'rising'
      state.entrancePhase.value = 'rising'
      await nextTick()
      if (token !== state.contentAnimToken.value) return false
      await sleep(CONTENT_RISE_MS)
      if (token !== state.contentAnimToken.value) return false
    }

    state.contentPhase.value = 'idle'
    state.entrancePhase.value = 'idle'
    return true
  }

  // Trigger the "enter main page" animation from the initial sunken state.
  // All areas slide in together: content from right, nav/breadcrumbs from left.
  async function playInitialAnimation(): Promise<void> {
    if (!state.initialRender.value || state.contentAnimating.value) return

    state.contentAnimating.value = true
    const token = ++state.contentAnimToken.value

    // Phase 0: Set up prep positions for ALL areas while initial-loading CSS
    // still hides them. Content at prep-right, nav+breadcrumbs at prep-left.
    state.contentPhase.value = 'slide-in-prep'
    state.entrancePhase.value = 'prep'

    // Now remove initial-loading — prep classes take over, so no visual jump.
    state.initialRender.value = false

    await nextTick()
    if (token !== state.contentAnimToken.value) return

    await playEntranceAnimation(token)
    state.contentAnimating.value = false
  }

  // Login transition: AuthPanel → user content. Sinks + slides out AuthPanel,
  // waits for data + style, then plays coordinated entrance animation.
  async function handleLoginTransition(): Promise<void> {
    state.contentAnimating.value = true
    const token = ++state.contentAnimToken.value

    // Phase 1: Sink AuthPanel
    state.contentPhase.value = 'sinking'
    await nextTick()
    if (token !== state.contentAnimToken.value) { state.contentAnimating.value = false; return }
    await sleep(CONTENT_SINK_MS)
    if (token !== state.contentAnimToken.value) { state.contentAnimating.value = false; return }

    // Phase 2: Slide out AuthPanel
    state.contentPhase.value = 'slide-out'
    await sleep(CONTENT_SLIDE_MS)
    if (token !== state.contentAnimToken.value) { state.contentAnimating.value = false; return }

    // Wait for data loading to complete
    if (ctx.isTransitioning.value) {
      await new Promise<void>(resolve => {
        const stop = watch(ctx.isTransitioning, (v) => {
          if (!v) { stop(); resolve() }
        })
      })
      if (token !== state.contentAnimToken.value) { state.contentAnimating.value = false; return }
    }

    // Hide nav/breadcrumbs/knob BEFORE Vue renders the new account data.
    // entrance-prep CSS positions them off-screen so the data swap is invisible.
    state.entrancePhase.value = 'prep'

    // Apply pending data — nav/breadcrumbs update behind entrance-prep hiding
    ctx.nodeStore.applyPendingData()

    // Empty account: skip entrance, show background
    if (ctx.display.showEmptyBackground.value) {
      state.displayedKey.value = ctx.display.contentKey.value
      state.displayedShowTree.value = false
      state.displayedNonTreeContent.value = ctx.display.nonTreeContent.value
      state.displayedSkipContentGlass.value = ctx.display.skipContentGlass.value
      state.treeMaskVisible.value = false
      state.treeOverlayActive.value = false
      state.entrancePhase.value = 'idle'
      state.contentPhase.value = 'idle'
      state.contentAnimating.value = false
      return
    }

    // Wait for user style to load so content reveals with correct colors
    if (!ctx.styleStore.loaded && ctx.authStore.isAuthenticated) {
      await new Promise<void>(resolve => {
        const stop = watch(() => ctx.styleStore.loaded, (v) => {
          if (v) { stop(); resolve() }
        })
      })
      if (token !== state.contentAnimToken.value) { state.contentAnimating.value = false; return }
    }

    // Swap DOM to new content at prep position (off-screen right)
    applyDisplayedState(ctx)
    state.treeOverlayActive.value = ctx.display.showTree.value
    state.contentPhase.value = 'slide-in-prep'

    await nextTick()
    if (token !== state.contentAnimToken.value) { state.contentAnimating.value = false; return }

    await playEntranceAnimation(token)
    state.contentAnimating.value = false
  }

  return { playEntranceAnimation, playInitialAnimation, handleLoginTransition }
}
