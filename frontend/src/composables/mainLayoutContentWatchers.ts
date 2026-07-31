import { watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/authStore'
import { useNodeStore } from '../stores/nodeStore'
import { usePageTransition } from './usePageTransition'
import { resetContentAnimation } from './mainLayoutContentContext'
import { CONTENT_DIRECT_STATES } from './useMainLayoutState'
import type { MainLayoutContentCtx } from './mainLayoutContentContext'

/**
 * All six content watchers. Must be invoked AFTER useMainLayoutLayout and
 * useMainLayoutCompactToggle in the entry so watcher registration order
 * matches the original (enableTransition < compactMode < these six).
 */
export function setupMainLayoutWatchers(
  ctx: MainLayoutContentCtx,
  animateContentTransition: () => Promise<void>,
): void {
  const { state } = ctx
  const { isTransitioning } = usePageTransition()
  const nodeStore = useNodeStore()
  const authStore = useAuthStore()
  const { initialized } = storeToRefs(authStore)

  // Trigger content animation when a page transition starts
  watch(isTransitioning, (transitioning) => {
    if (transitioning) {
      state.treeWasVisible.value = ctx.display.showTree.value

      if (state.contentAnimating.value) {
        state.contentAnimToken.value++
        state.contentPhase.value = 'idle'
        resetContentAnimation(ctx)
      }
      animateContentTransition()
    } else {
      // Transition ended — clean up tree curtain
      if (!ctx.display.showTree.value) {
        state.treeCurtainDrawn.value = false
      }
    }
  })

  // Keep displayed refs in sync when not animating (e.g. dev mode with transitions disabled)
  watch(() => ctx.display.contentKey.value, (_newKey, oldKey) => {
    if (oldKey === 'loading') return
    if (!state.contentAnimating.value && state.contentPhase.value === 'idle') {
      // When transitioning from unauthenticated→authenticated (login), don't
      // reactively overwrite display refs. The login animation orchestrates the
      // DOM swap; overwriting here would break the login detection.
      if (ctx.authStore.isAuthenticated && oldKey.startsWith('auth:')) return

      state.displayedKey.value = ctx.display.contentKey.value
      state.displayedShowTree.value = ctx.display.showTree.value
      state.displayedNonTreeContent.value = ctx.display.nonTreeContent.value
      state.displayedSkipContentGlass.value = ctx.display.skipContentGlass.value
      state.treeMaskVisible.value = false
      state.treeOverlayActive.value = ctx.display.showTree.value
    }
  })

  // Directly trigger content animation when viewState enters/leaves
  // CONTENT_DIRECT_STATES. The isTransitioning-based watcher may not fire for
  // synchronous viewState transitions (isTransitioning goes true→false in-tick).
  watch(() => nodeStore.viewState, (newState, oldState) => {
    if (state.contentAnimating.value) return

    const wasSpecial = CONTENT_DIRECT_STATES.includes(oldState)
    const isSpecial = CONTENT_DIRECT_STATES.includes(newState)

    // Only animate for special ↔ non-special transitions
    if (wasSpecial === isSpecial) return

    // Don't double-trigger with isTransitioning watcher
    if (isTransitioning.value) return

    state.treeWasVisible.value = ctx.display.showTree.value
    animateContentTransition()
  })

  // When login completes (isAuthenticated false→true), hide nav/breadcrumbs/knob
  // BEFORE Vue re-renders with the new account data. Vue watchers fire
  // pre-flush, so entrancePhase is set before the DOM updates.
  watch(() => authStore.isAuthenticated, (now, prev) => {
    if (now && !prev && !state.initialRender.value) {
      state.entrancePhase.value = 'prep'
    }
  })

  // When auth initialization completes and the user is not authenticated,
  // animate the transition from skeleton to AuthPanel.
  watch(initialized, (nowInitialized, prevInitialized) => {
    if (nowInitialized && !prevInitialized && !ctx.authStore.isAuthenticated && !state.contentAnimating.value) {
      animateContentTransition()
    }
  })

  // Tree curtain: tracks visibility across transitions
  watch(
    [() => state.treeCanvasRef.value?.sceneReady, () => ctx.display.showTree.value],
    ([ready, treeVisible]) => {
      if (!state.treeCurtainDrawn.value) return

      if (!treeVisible) {
        state.treeCurtainDrawn.value = false
        return
      }

      if (ready) {
        state.treeCurtainDrawn.value = false
      }
    },
  )
}
