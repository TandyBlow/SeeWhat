import * as THREE from 'three'
import { useNodeStore } from '../../stores/nodeStore'
import { useStyleStore } from '../../stores/styleStore'
import { cinemaTreeCanvas } from '../../composables/useCinemaBridge'
import type { CinematicShared, AccountSnap } from './useCinematicShared'
import type { CinematicAccounts } from './useCinematicAccounts'

/**
 * Phase 2 three.js scene wiring: fetches /demo_styles.json, preloads background
 * textures, and runs the quadratic-accelerating style-cycle animation loop.
 */
export function useCinematicPhase2(shared: CinematicShared, accounts: CinematicAccounts) {
  const nodeStore = useNodeStore()
  const styleStore = useStyleStore()

  async function loadDemoStyles() {
    try {
      const resp = await fetch('/demo_styles.json')
      if (!resp.ok) {
        console.warn('[CinemaDemo] demo_styles.json not found, style cycling disabled')
        return
      }
      const data = await resp.json()
      shared.demoStyles.value = data
    } catch (e) {
      console.warn('[CinemaDemo] failed to load demo_styles.json:', e)
    }
  }

  function preloadBackgroundTextures() {
    const loader = new THREE.TextureLoader()
    for (const style of shared.demoStyles.value) {
      const path = style.bgPath || `/backgrounds/ai/demo_style_${String(style.index).padStart(3, '0')}.png`
      loader.load(
        path,
        (texture) => {
          shared.preloadedTextures.set(style.index, texture)
          if (shared.preloadedTextures.size === shared.demoStyles.value.length) {
            // all background textures preloaded
          }
        },
        undefined,
        () => {
          // Silently skip failed textures — they'll just use whatever is current
        },
      )
    }
  }

  function deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj))
  }

  async function runPhase2() {
    const gamedevSnap = shared.snapshots.get('gamedev')!
    accounts.injectAccount(gamedevSnap)
    nodeStore.loadNode(null)
    await accounts.waitForSettle('display')

    const originalParams = deepClone(styleStore.styleParams)
    const originalBgUrl = styleStore.backgroundUrl
    const styles = shared.demoStyles.value
    const textures = shared.preloadedTextures

    if (styles.length === 0) {
      console.warn('[CinemaDemo] no demo styles loaded, skipping Phase 2')
      shared.demoPhase.value = 'done'
      return
    }

    const totalDuration = 15000
    const startTime = performance.now()
    let styleProgress = 0
    let currentStyleIdx = -1
    let lastRebuildTime = 0
    let lastFrameTime = startTime

    const animate = () => {
      const now = performance.now()
      const elapsed = now - startTime
      const deltaTime = now - lastFrameTime
      lastFrameTime = now

      if (elapsed >= totalDuration || shared.cancelled.value) {
        cancelAnimationFrame(shared.phase2AnimFrame.value)
        finishPhase2(originalParams, originalBgUrl, gamedevSnap)
        return
      }

      const progress = elapsed / totalDuration
      const gm = 0.3 + progress * 2.2

      // Style interval: 800ms → 30ms (quadratic acceleration)
      const interval = 800 - (800 - 30) * progress * progress
      styleProgress += deltaTime / interval
      const targetIdx = Math.min(styles.length - 1, Math.floor(styleProgress))

      const canvas = cinemaTreeCanvas.value
      if (!canvas) {
        shared.phase2AnimFrame.value = requestAnimationFrame(animate)
        return
      }

      if (targetIdx > currentStyleIdx) {
        currentStyleIdx = targetIdx
        const dur = Math.max(60, interval * 0.7)
        canvas.transitionToParamsDirect(styles[currentStyleIdx]!.params, dur)
        styleStore.applyThemeFromParams(styles[currentStyleIdx]!.params)
        const tex = textures.get(currentStyleIdx)
        if (tex) canvas.swapBackgroundTexture(tex)
      }

      // Rebuild tree geometry every 250ms at the current growth level
      if (elapsed - lastRebuildTime > 250) {
        lastRebuildTime = elapsed
        canvas.setGrowthLevel(gm, 18, 3)
        canvas.setTreeGroupScale(1.0)
      } else {
        const baseGM = 0.3 + (lastRebuildTime / totalDuration) * 2.2
        const scale = gm / Math.max(0.01, baseGM)
        canvas.setTreeGroupScale(Math.max(0.3, Math.min(2.0, scale)))
      }

      shared.phase2AnimFrame.value = requestAnimationFrame(animate)
    }

    shared.phase2AnimFrame.value = requestAnimationFrame(animate)
  }

  function finishPhase2(originalParams: any, originalBgUrl: string | null, gamedevSnap: AccountSnap) {
    const canvas = cinemaTreeCanvas.value
    if (canvas) {
      canvas.setGrowthLevel(2.5, 18, 3)
      canvas.setTreeGroupScale(1.0)
      canvas.getManager()?.applyStyleParamsPublic(originalParams)
    }
    styleStore.forceStyle(gamedevSnap.styleName, gamedevSnap.distribution, originalParams, originalBgUrl)
    shared.demoPhase.value = 'done'
  }

  return { loadDemoStyles, preloadBackgroundTextures, runPhase2 }
}

export type CinematicPhase2 = ReturnType<typeof useCinematicPhase2>
