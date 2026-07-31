import { nextTick } from 'vue'
import type { Ref } from 'vue'
import { useNodeStore } from '../stores/nodeStore'
import { useAuthStore } from '../stores/authStore'
import { useStyleStore } from '../stores/styleStore'
import { usePageTransition } from './usePageTransition'
import { createSceneWait } from './mainLayoutSceneWait'
import { CONTENT_RISE_MS, sleep } from './useMainLayoutState'
import type { MainLayoutState } from './useMainLayoutState'
import type { MainLayoutDisplay } from './useMainLayoutDisplay'

/**
 * Shared MainLayoutContentCtx object passed into every content/entrance/
 * compact/official composable and every path helper. Built once during setup.
 */
export interface MainLayoutContentCtx {
  state: MainLayoutState
  display: MainLayoutDisplay
  waitForSceneReady: (token: number) => Promise<void>
  nodeStore: ReturnType<typeof useNodeStore>
  authStore: ReturnType<typeof useAuthStore>
  styleStore: ReturnType<typeof useStyleStore>
  isTransitioning: Ref<boolean>
}

export function createMainLayoutContentCtx(opts: {
  state: MainLayoutState
  display: MainLayoutDisplay
}): MainLayoutContentCtx {
  const { state, display } = opts
  const { waitForSceneReady } = createSceneWait(state)
  return {
    state,
    display,
    waitForSceneReady,
    nodeStore: useNodeStore(),
    authStore: useAuthStore(),
    styleStore: useStyleStore(),
    isTransitioning: usePageTransition().isTransitioning,
  }
}

// The 4 common displayed-ref assignments shared by every DOM-swap site.
export function applyDisplayedState(ctx: MainLayoutContentCtx): void {
  ctx.state.displayedSkipContentGlass.value = ctx.display.skipContentGlass.value
  ctx.state.displayedKey.value = ctx.display.contentKey.value
  ctx.state.displayedShowTree.value = ctx.display.showTree.value
  ctx.state.displayedNonTreeContent.value = ctx.display.nonTreeContent.value
}

// Empty-background shortcut: show background, cancel animation state.
export function applyEmptyBackground(ctx: MainLayoutContentCtx): void {
  ctx.state.displayedKey.value = ctx.display.contentKey.value
  ctx.state.displayedShowTree.value = false
  ctx.state.displayedNonTreeContent.value = ctx.display.nonTreeContent.value
  ctx.state.displayedSkipContentGlass.value = ctx.display.skipContentGlass.value
  ctx.state.treeMaskVisible.value = false
  ctx.state.treeOverlayActive.value = false
  ctx.state.contentPhase.value = 'idle'
  ctx.state.contentAnimating.value = false
}

// Cancel an in-flight content animation: sync displayed refs + mask/overlay.
// NOTE: contentAnimToken++ and contentPhase='idle' must stay at each call site
// (the original blocks differ in those extras).
export function resetContentAnimation(ctx: MainLayoutContentCtx): void {
  applyDisplayedState(ctx)
  ctx.state.treeMaskVisible.value = false
  ctx.state.treeOverlayActive.value = ctx.display.showTree.value
  ctx.state.contentAnimating.value = false
}

// Rise — glass frame regains shadow (skip when current wrapper is
// content-direct, which has no glass frame to rise). Ends with idle state.
export async function applyRise(ctx: MainLayoutContentCtx, token: number): Promise<void> {
  if (!ctx.state.displayedSkipContentGlass.value) {
    ctx.state.contentPhase.value = 'rising'
    await nextTick()
    if (token !== ctx.state.contentAnimToken.value) return
    await sleep(CONTENT_RISE_MS)
    if (token !== ctx.state.contentAnimToken.value) return
  }
  ctx.state.contentPhase.value = 'idle'
  ctx.state.contentAnimating.value = false
}
