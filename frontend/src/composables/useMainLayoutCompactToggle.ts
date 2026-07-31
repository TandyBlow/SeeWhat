import { watch, nextTick } from 'vue'
import { useKnobDispatch } from './useKnobDispatch'
import type { CompactMode } from './useKnobDispatch'
import { usePageTransition } from './usePageTransition'
import { useNodeStore } from '../stores/nodeStore'
import { applyDisplayedState } from './mainLayoutContentContext'
import { CONTENT_DIRECT_STATES, CONTENT_SINK_MS, CONTENT_SLIDE_MS, CONTENT_RISE_MS, TREE_MASK_FADE_MS, sleep } from './useMainLayoutState'
import type { MainLayoutContentCtx } from './mainLayoutContentContext'

/**
 * Small-layout compact toggle (content↔nav). Extracted verbatim.
 */
export function useMainLayoutCompactToggle(ctx: MainLayoutContentCtx): void {
  const { state } = ctx
  const { layoutType, compactMode } = useKnobDispatch()
  const { isTransitioning } = usePageTransition()
  const nodeStore = useNodeStore()

  // ================================================================
  // Compact toggle animation (small layout only)
  // Tree path: mask fade-in/out (same mechanism as large layout)
  // Non-tree path: sink → slide-out → slide-in → rise
  // ================================================================
  async function animateCompactToggle(_oldMode: CompactMode, newMode: CompactMode): Promise<void> {
    const navEl = state.navigationRef.value
    const contentEl = state.contentAreaRef.value
    if (!navEl || !contentEl) return

    state.contentAnimating.value = true
    const token = ++state.contentAnimToken.value
    const toNav = newMode === 'nav'

    if (toNav) {
      // Content → Nav

      // Exit any special state so the user returns to display mode.
      const specialStates = ['move', 'delete', ...CONTENT_DIRECT_STATES]
      if (specialStates.includes(nodeStore.viewState)) {
        nodeStore.setViewState('display')
      }

      if (state.displayedShowTree.value) {
        // ---- TREE PATH: mask fade-in covers the tree ----

        state.treeMaskVisible.value = true
        state.contentPhase.value = 'tree-mask'
        await sleep(TREE_MASK_FADE_MS)
        if (token !== state.contentAnimToken.value) return

        // Snap mask off — content area is about to be hidden
        const maskEl = state.treeMaskRef.value
        if (maskEl) maskEl.style.transition = 'none'
        state.treeMaskVisible.value = false
        state.treeOverlayActive.value = false
        state.contentPhase.value = 'idle'

        await nextTick()
        void maskEl?.offsetHeight
        if (maskEl) maskEl.style.transition = ''
        if (token !== state.contentAnimToken.value) return
      } else {
        // ---- NON-TREE PATH: slide-out right ----

        state.contentPhase.value = 'sinking'
        await nextTick()
        if (token !== state.contentAnimToken.value) return
        await sleep(CONTENT_SINK_MS)
        if (token !== state.contentAnimToken.value) return

        state.contentPhase.value = 'slide-out'
        await sleep(CONTENT_SLIDE_MS)
        if (token !== state.contentAnimToken.value) return

        state.contentPhase.value = 'idle'
      }

      // Swap visibility — hide content, show nav in prep position
      contentEl.style.display = 'none'
      navEl.style.display = ''
      state.compactAnimPhase.value = 'nav-slide-in-prep'

      await nextTick()
      void navEl.offsetHeight

      // Nav slides in from left as sunken
      state.compactAnimPhase.value = 'nav-slide-in'
      await sleep(CONTENT_SLIDE_MS)
      if (token !== state.contentAnimToken.value) return

      // Nav rises — glass items regain shadow
      state.compactAnimPhase.value = 'rising'
      await nextTick()
      await sleep(CONTENT_RISE_MS)
    } else {
      // Nav → Content

      // Nav sinks
      state.compactAnimPhase.value = 'sinking'
      await nextTick()
      await sleep(CONTENT_SINK_MS)

      // Nav slides out left
      state.compactAnimPhase.value = 'nav-slide-out'
      await sleep(CONTENT_SLIDE_MS)

      // Apply pending node data so showTree reflects the actual state
      nodeStore.applyPendingData()

      // Swap visibility — hide nav, show content
      state.compactAnimPhase.value = 'idle'
      navEl.style.display = 'none'
      contentEl.style.display = ''

      if (ctx.display.showTree.value) {
        // ---- TREE PATH: mask covers tree while it loads, then fades out ----

        // Snap mask to visible instantly (no fade-in)
        state.treeOverlayActive.value = true
        const maskEl = state.treeMaskRef.value
        if (maskEl) maskEl.style.transition = 'none'
        state.treeMaskVisible.value = true

        // Swap DOM: tree loads under the fully opaque mask
        applyDisplayedState(ctx)
        state.contentPhase.value = 'tree-mask'

        await nextTick()
        if (token !== state.contentAnimToken.value) return
        const ctTreeReflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
        void ctTreeReflowEl?.offsetHeight
        if (maskEl) maskEl.style.transition = ''

        // Wait for tree scene to be ready, then fade mask out
        await nextTick()
        await ctx.waitForSceneReady(token)
        if (token !== state.contentAnimToken.value) return
        state.treeMaskVisible.value = false
        await sleep(TREE_MASK_FADE_MS)
        if (token !== state.contentAnimToken.value) return
      } else {
        // ---- NON-TREE PATH: slide-in from right ----

        applyDisplayedState(ctx)
        state.contentPhase.value = 'slide-in-prep'

        await nextTick()
        if (token !== state.contentAnimToken.value) return

        const ctReflowEl = state.contentGlassRef.value || document.querySelector('.content-direct')
        void ctReflowEl?.offsetHeight
        state.contentPhase.value = 'slide-in'
        await sleep(CONTENT_SLIDE_MS)
        if (token !== state.contentAnimToken.value) return

        // Content rises — glass items regain shadow
        state.contentPhase.value = 'rising'
        await nextTick()
        await sleep(CONTENT_RISE_MS)
      }
    }

    state.contentPhase.value = 'idle'
    state.compactAnimPhase.value = 'idle'
    state.contentAnimating.value = false
  }

  watch(compactMode, (newMode, oldMode) => {
    if (newMode === oldMode || layoutType.value !== 'small') return
    if (isTransitioning.value) return
    if (state.contentAnimating.value) return
    animateCompactToggle(oldMode as CompactMode, newMode as CompactMode)
  })
}
