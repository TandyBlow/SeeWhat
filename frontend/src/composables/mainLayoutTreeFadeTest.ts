import { nextTick } from 'vue'
import { CONTENT_SINK_MS, CONTENT_RISE_MS, TREE_MASK_FADE_MS, sleep } from './useMainLayoutState'
import type { MainLayoutContentCtx } from './mainLayoutContentContext'

// Dev-only: trigger the tree fade-out animation for testing/debugging.
// When tree is showing, fades the mask in (tree disappears), holds briefly,
// then fades the mask out (tree reappears).
export function createTreeFadeTest(ctx: MainLayoutContentCtx): () => Promise<void> {
  const { state } = ctx

  return async function triggerTreeFadeTest(): Promise<void> {
    if (state.contentAnimating.value) {
      state.contentAnimToken.value++
      state.contentPhase.value = 'idle'
      state.treeMaskVisible.value = false
      state.contentAnimating.value = false
    }

    if (!state.displayedShowTree.value) {
      return
    }

    state.contentAnimating.value = true
    const token = ++state.contentAnimToken.value

    // Phase 1: Sink
    state.contentPhase.value = 'sinking'
    await nextTick()
    await sleep(CONTENT_SINK_MS)
    if (token !== state.contentAnimToken.value) return

    // Phase 2: Mask fades in — tree disappears behind mask
    state.treeMaskVisible.value = true
    state.contentPhase.value = 'tree-mask'
    await sleep(TREE_MASK_FADE_MS)
    if (token !== state.contentAnimToken.value) return

    // Hold for visual observation
    await sleep(1000)

    // Phase 3: Fade mask back out — tree reappears
    state.treeMaskVisible.value = false
    await sleep(TREE_MASK_FADE_MS)
    if (token !== state.contentAnimToken.value) return

    // Phase 4: Rise
    state.contentPhase.value = 'rising'
    await nextTick()
    await sleep(CONTENT_RISE_MS)

    state.contentPhase.value = 'idle'
    state.contentAnimating.value = false
  }
}
