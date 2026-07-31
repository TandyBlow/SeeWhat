import type { NavigationState } from './NavigationState'

// Pure two-phase scroll-step: phase1 slides the row out, phase2 commits the
// new row and realigns the window. Reads/writes the shared state bag so the
// scrollCancelToken guards invalidate stale callbacks across resets.
export function animateSingleScroll(state: NavigationState, direction: 'up' | 'down', totalMs: number): Promise<void> {
  const token = ++state.scrollCancelToken
  const phase1Ms = Math.round(totalMs * 0.35)
  const phase2Ms = Math.round(totalMs * 0.55)

  state.scrollDirection.value = direction

  return new Promise<void>((resolve) => {
    if (direction === 'down') {
      const topId = state.displayItems.value[0]?.id
      const newItem = state.scrollSource.value[state.scrollOffset.value + state.maxVisible.value]
      if (!topId || !newItem) { resolve(); return }

      state.scrollingTopId.value = topId

      setTimeout(() => {
        if (token !== state.scrollCancelToken) { resolve(); return }
        state.scrollingTopId.value = null
        state.scrollingBottomId.value = newItem.id
        state.displayItems.value = [...state.displayItems.value.slice(1), newItem]
        state.scrollOffset.value = state.scrollOffset.value + 1

        setTimeout(() => {
          if (token !== state.scrollCancelToken) { resolve(); return }
          state.scrollingBottomId.value = null
          state.scrollDirection.value = null
          state.displayItems.value = state.scrollSource.value.slice(
            state.scrollOffset.value,
            state.scrollOffset.value + state.maxVisible.value,
          )
          resolve()
        }, phase2Ms)
      }, phase1Ms)
    } else {
      const bottomId = state.displayItems.value[state.displayItems.value.length - 1]?.id
      const newItem = state.scrollSource.value[state.scrollOffset.value - 1]
      if (!bottomId || !newItem) { resolve(); return }

      state.scrollingBottomId.value = bottomId

      setTimeout(() => {
        if (token !== state.scrollCancelToken) { resolve(); return }
        state.scrollingBottomId.value = null
        state.scrollingTopId.value = newItem.id
        state.displayItems.value = [newItem, ...state.displayItems.value.slice(0, -1)]
        state.scrollOffset.value = state.scrollOffset.value - 1

        setTimeout(() => {
          if (token !== state.scrollCancelToken) { resolve(); return }
          state.scrollingTopId.value = null
          state.scrollDirection.value = null
          state.displayItems.value = state.scrollSource.value.slice(
            state.scrollOffset.value,
            state.scrollOffset.value + state.maxVisible.value,
          )
          resolve()
        }, phase2Ms)
      }, phase1Ms)
    }
  })
}
