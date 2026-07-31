import { ref, computed } from 'vue'

export function useStreamingElapsed() {
  const startTime = ref(0)
  const elapsedMs = ref(0)
  let elapsedTimer: ReturnType<typeof setInterval> | null = null

  const elapsedDisplay = computed(() => {
    const s = Math.floor(elapsedMs.value / 1000)
    return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
  })

  function start() {
    startTime.value = Date.now()
    elapsedTimer = setInterval(() => {
      elapsedMs.value = Date.now() - startTime.value
    }, 200)
  }

  function stop() {
    if (elapsedTimer) {
      clearInterval(elapsedTimer)
      elapsedTimer = null
    }
  }

  return { elapsedDisplay, start, stop }
}
