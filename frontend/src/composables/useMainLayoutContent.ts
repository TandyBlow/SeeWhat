import { provide, nextTick, watch } from 'vue'
import { useKnobDispatch } from './useKnobDispatch'
import { usePageTransition } from './usePageTransition'
import { useOfficialTransition } from './useOfficialTransition'
import { resetContentAnimation, applyDisplayedState, applyEmptyBackground } from './mainLayoutContentContext'
import { handleTreeExit, handleNonTreePath } from './mainLayoutContentPaths'
import { handleSpecialStateExit } from './mainLayoutContentSpecialPath'
import { createTreeFadeTest } from './mainLayoutTreeFadeTest'
import { CONTENT_DIRECT_STATES, CONTENT_SINK_MS, sleep } from './useMainLayoutState'
import AuthPanel from '../components/auth/AuthPanel.vue'
import type { MainLayoutContentCtx } from './mainLayoutContentContext'
import type { MainLayoutEntrance } from './useMainLayoutEntrance'

export interface MainLayoutContent {
  animateContentTransition: () => Promise<void>
  triggerTreeFadeTest: () => Promise<void>
}

/**
 * Content transition orchestrator. Creates provides and dispatches to the
 * extracted path helpers. Watchers live in mainLayoutContentWatchers.ts.
 */
export function useMainLayoutContent(
  ctx: MainLayoutContentCtx,
  entrance: MainLayoutEntrance,
): MainLayoutContent {
  const { state } = ctx
  const { layoutType, compactMode } = useKnobDispatch()
  const { isTransitioning } = usePageTransition()
  const { animating: otAnimating } = useOfficialTransition()

  // Track previous viewState to detect small-layout special-state transitions.
  // Must persist across animateContentTransition calls (mutable closure let).
  let prevCompactViewState = ctx.nodeStore.viewState

  provide('contentAnimating', state.contentAnimating)

  // ================================================================
  // Content transition animation
  // Tree: mask fade-in/out (no slide)
  // Non-tree: sink → slide-out → slide-in → rise
  // ================================================================
  async function animateContentTransition(): Promise<void> {
    if (state.contentAnimating.value) {
      state.contentAnimToken.value++
      state.contentPhase.value = 'idle'
      state.compactAnimPhase.value = 'idle'
      resetContentAnimation(ctx)
      return
    }

    // When content area is hidden in compact nav mode, stay in the nav and let
    // the nav's own animateNavPageTransition handle the visual update. Wait for
    // data loading to finish first — without this, a cold cache means
    // pendingNodeContext is still null and the nav renders a blank list.
    if (layoutType.value === 'small' && compactMode.value === 'nav') {
      if (isTransitioning.value) {
        const ct = state.contentAnimToken.value
        await new Promise<void>(resolve => {
          const stop = watch(isTransitioning, (v) => {
            if (!v) { stop(); resolve() }
          })
        })
        if (ct !== state.contentAnimToken.value) return
      }
      ctx.nodeStore.applyPendingData()
      return
    }

    // Initial page load: content starts sunken (only bottom areas visible).
    // Data loads silently; entrance animation auto-plays when ready.
    if (state.initialRender.value) {
      const sameContent = ctx.display.contentKey.value === state.displayedKey.value && ctx.display.showTree.value === state.displayedShowTree.value
      if (sameContent && ctx.nodeStore.viewState === prevCompactViewState) {
        ctx.nodeStore.applyPendingData()
        return
      }

      // Wait for data loading to complete (executeDataLoading runs in startTransition).
      if (isTransitioning.value) {
        await new Promise<void>(resolve => {
          const stop = watch(isTransitioning, (v) => {
            if (!v) { stop(); resolve() }
          })
        })
      }

      ctx.nodeStore.applyPendingData()

      // Wait for style to load before revealing bottom areas.
      // Unauthenticated users always use default CSS style, no wait needed.
      if (!ctx.styleStore.loaded && ctx.authStore.isAuthenticated) {
        await new Promise<void>(resolve => {
          const stop = watch(() => ctx.styleStore.loaded, (v) => {
            if (v) { stop(); resolve() }
          })
        })
      }

      // Update displayed refs silently — content stays hidden by initial-loading CSS
      state.displayedSkipContentGlass.value = ctx.display.skipContentGlass.value
      state.displayedKey.value = ctx.display.contentKey.value
      state.displayedShowTree.value = ctx.display.showTree.value
      state.displayedNonTreeContent.value = ctx.display.nonTreeContent.value
      state.treeOverlayActive.value = ctx.display.showTree.value

      // Trigger the coordinated entrance animation (content, nav, breadcrumbs, knob)
      entrance.playInitialAnimation()
      return
    }

    // Login transition: AuthPanel → user content.
    if (ctx.authStore.isAuthenticated && state.displayedNonTreeContent.value === AuthPanel) {
      await entrance.handleLoginTransition()
      return
    }

    // Safety: reset entrancePhase in case a pre-flush watcher set it to 'prep'
    // for a login that didn't route through handleLoginTransition.
    state.entrancePhase.value = 'idle'

    // When entering or leaving a CONTENT_DIRECT_STATES view, the wrapper
    // element changes between content-glass and content-direct.
    const wasSpecial = CONTENT_DIRECT_STATES.includes(prevCompactViewState)
    const isSpecial = CONTENT_DIRECT_STATES.includes(ctx.nodeStore.viewState)
    prevCompactViewState = ctx.nodeStore.viewState

    if (wasSpecial || isSpecial) {
      // Official transition orchestrator handles its own animation
      if (otAnimating.value) return

      if (!wasSpecial && isSpecial) {
        // Entering special state: fall through to animation below. Old content
        // (in content-glass) sinks + slides out, new content (in content-direct)
        // slides in, no rise.
      } else if (wasSpecial && !isSpecial) {
        await handleSpecialStateExit(ctx)
        return
      } else {
        // special→special: instant swap
        applyDisplayedState(ctx)
        state.treeMaskVisible.value = false
        state.treeOverlayActive.value = ctx.display.showTree.value
        return
      }
    }

    state.contentAnimating.value = true
    const token = ++state.contentAnimToken.value
    const oldKey = state.displayedKey.value
    const wasShowingTree = state.displayedShowTree.value

    // Empty account with no nodes: skip animation, just show background
    if (ctx.display.showEmptyBackground.value) {
      applyEmptyBackground(ctx)
      return
    }

    // Phase 1: Sink — glass frame loses shadow, content fades
    state.contentPhase.value = 'sinking'
    await nextTick()
    if (token !== state.contentAnimToken.value) return
    await sleep(CONTENT_SINK_MS)
    if (token !== state.contentAnimToken.value) return

    // Wait for data loading to complete before applying pending data.
    if (isTransitioning.value) {
      await new Promise<void>(resolve => {
        const stop = watch(isTransitioning, (v) => {
          if (!v) { stop(); resolve() }
        })
      })
      if (token !== state.contentAnimToken.value) return
    }

    if (wasShowingTree) {
      await handleTreeExit(ctx, token, oldKey)
    } else {
      await handleNonTreePath(ctx, token, oldKey)
    }
  }

  const triggerTreeFadeTest = createTreeFadeTest(ctx)
  provide('triggerTreeFadeTest', triggerTreeFadeTest)

  return { animateContentTransition, triggerTreeFadeTest }
}
