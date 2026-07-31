<template>
  <div class="cinema-overlay">
    <!-- Loading -->
    <Transition name="fade">
      <div v-if="demoPhase === 'loading'" class="cinema-loading">
        <div class="loading-ring" />
        <p class="loading-text">{{ loadingText }}</p>
      </div>
    </Transition>

    <!-- Phase 1 control bar -->
    <div v-if="demoPhase === 'phase1' && ready" class="cinema-controls">
      <button class="ctrl-btn" @click="prevScene" :disabled="busy">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <button class="ctrl-btn" @click="togglePause">
        <svg v-if="paused" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
        <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
      </button>
      <button class="ctrl-btn" @click="nextScene" :disabled="busy">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
      <div class="ctrl-dots">
        <span v-for="(s, i) in phase1Scenes" :key="s.id" class="ctrl-dot" :class="{ active: i === phase1Idx }" @click="jumpToPhase1Scene(i)" />
      </div>
      <span class="ctrl-label" v-if="phase1Scenes[phase1Idx]">{{ phase1Scenes[phase1Idx]!.label }}</span>
    </div>

    <!-- Blackout transition -->
    <Transition name="fade">
      <div v-if="demoPhase === 'blackout'" class="blackout-overlay" />
    </Transition>

    <!-- Done label -->
    <Transition name="fade">
      <div v-if="demoPhase === 'done'" class="done-label">Acacia</div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '../../stores/authStore'
import { LOCAL_SESSION_KEY } from '../../constants/app'
import { useCinematicShared } from './useCinematicShared'
import { useCinematicAccounts } from './useCinematicAccounts'
import { useCinematicPhase2 } from './useCinematicPhase2'
import { useCinematicSequencer } from './useCinematicSequencer'
import { useCinematicInit } from './useCinematicInit'

const { t } = useI18n()

const shared = useCinematicShared()
const { demoPhase, ready, busy, paused, loadingText, phase1Scenes, phase1Idx } = shared

loadingText.value = t('demo.preparing')

const accounts = useCinematicAccounts(shared)
const phase2 = useCinematicPhase2(shared, accounts)
const sequencer = useCinematicSequencer(shared, accounts, phase2)
useCinematicInit(shared, accounts, phase2, sequencer)

const { togglePause, nextScene, prevScene, jumpToPhase1Scene } = sequencer

onBeforeUnmount(() => {
  shared.cancelled.value = true
  sequencer.clearAdvanceTimer()
  if (shared.phase2AnimFrame.value) cancelAnimationFrame(shared.phase2AnimFrame.value)
  // Remove persisted auth so demo accounts don't leak into normal mode
  localStorage.removeItem(LOCAL_SESSION_KEY)
  localStorage.removeItem('auth')
  useAuthStore().logout()
})
</script>

<style scoped src="./CinematicDemo.1.css"></style>
