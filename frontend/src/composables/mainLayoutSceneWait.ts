import { watch, onBeforeUnmount } from 'vue'
import { useDevStore } from '../stores/devStore'
import type { MainLayoutState } from './useMainLayoutState'

/**
 * Factory createSceneWait(state) returning { waitForSceneReady } and
 * registering its own onBeforeUnmount to clear lingering watchers.
 * Must be created during setup (it calls watch/onBeforeUnmount).
 */
export function createSceneWait(state: MainLayoutState) {
  const devStore = useDevStore()
  const activeSceneWatchers = new Set<() => void>()

  function waitForSceneReady(token: number): Promise<void> {
    return new Promise((resolve) => {
      let resolved = false
      const watchers: (() => void)[] = []

      const done = () => {
        if (resolved) return
        resolved = true
        watchers.forEach(stop => {
          stop()
          activeSceneWatchers.delete(stop)
        })
        resolve()
      }

      if (state.treeCanvasRef.value?.sceneReady && !devStore.manualSceneReady) {
        done()
        return
      }

      // Notify DevPanel we're waiting
      window.dispatchEvent(new CustomEvent('dev-waiting-for-scene'))

      // In manual mode, wait for dev-scene-ready event
      if (devStore.manualSceneReady) {
        const onManualReady = () => {
          window.removeEventListener('dev-scene-ready', onManualReady)
          done()
        }
        window.addEventListener('dev-scene-ready', onManualReady)

        const checkCancel = watch(
          () => state.contentAnimToken.value,
          (currentToken) => {
            if (currentToken !== token) {
              window.removeEventListener('dev-scene-ready', onManualReady)
              done()
            }
          },
        )
        watchers.push(checkCancel)
        activeSceneWatchers.add(checkCancel)
        return
      }

      // Auto mode: watch sceneReady
      const stop = watch(
        () => state.treeCanvasRef.value?.sceneReady,
        (ready) => {
          if (ready) {
            done()
          }
        },
      )
      watchers.push(stop)
      activeSceneWatchers.add(stop)

      const checkCancel = watch(
        () => state.contentAnimToken.value,
        (currentToken) => {
          if (currentToken !== token) {
            done()
          }
        },
      )
      watchers.push(checkCancel)
      activeSceneWatchers.add(checkCancel)
    })
  }

  onBeforeUnmount(() => {
    // Clean up any lingering waitForSceneReady watchers
    activeSceneWatchers.forEach(stop => stop())
    activeSceneWatchers.clear()
  })

  return { waitForSceneReady }
}
