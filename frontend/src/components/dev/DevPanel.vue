<template>
  <Teleport to="body">
    <DevPanelPanel
      v-if="isExpanded"
      :current-style-name="currentStyleName"
      :locale="locale"
      :style-regen-running="styleRegenRunning"
      :tree-fade-running="treeFadeRunning"
      :reset-growth-running="resetGrowthRunning"
      :logout-running="logoutRunning"
      :profile-loading="profileLoading"
      :demo-switch-running="demoSwitchRunning"
      @close="isExpanded = false"
      @switch-locale="switchLocale"
      @style-regen="onStyleRegen"
      @reset-style="onResetStyle"
      @tree-fade-test="onTreeFadeTest"
      @reset-growth="onResetGrowth"
      @logout="onLogout"
      @show-profile="onShowProfileText"
      @switch-demo-account="onSwitchDemoAccount"
    />
    <DevPanelProfile v-if="profileVisible" :profile="profileData" @close="profileVisible = false" />
    <!-- Floating Scene Ready button — always visible when waiting -->
    <button
      v-if="waitingForScene"
      type="button"
      class="scene-ready-btn"
      @click="emitSceneReady"
    >
      Scene Ready
    </button>
    <button v-if="!isExpanded && !waitingForScene" class="dev-panel-trigger" @click="isExpanded = true">
      <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="9" cy="9" r="2.5" />
        <path d="M9 1.5v2M9 14.5v2M1.5 9h2M14.5 9h2M3.7 3.7l1.4 1.4M12.9 12.9l1.4 1.4M3.7 14.3l1.4-1.4M12.9 5.1l1.4-1.4" />
      </svg>
    </button>
  </Teleport>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import DevPanelPanel from './DevPanelPanel.vue'
import DevPanelProfile from './DevPanelProfile.vue'
import { useDevPanelActions } from './useDevPanelActions'

const { t, locale } = useI18n()
const {
  isExpanded,
  waitingForScene,
  currentStyleName,
  styleRegenRunning,
  treeFadeRunning,
  resetGrowthRunning,
  logoutRunning,
  profileLoading,
  profileVisible,
  demoSwitchRunning,
  profileData,
  switchLocale,
  onLogout,
  onTreeFadeTest,
  emitSceneReady,
  onStyleRegen,
  onResetStyle,
  onResetGrowth,
  onShowProfileText,
  onSwitchDemoAccount,
  onWaitingForScene,
} = useDevPanelActions(t, locale)

onMounted(() => {
  window.addEventListener('dev-waiting-for-scene', onWaitingForScene)
})

onBeforeUnmount(() => {
  window.removeEventListener('dev-waiting-for-scene', onWaitingForScene)
})
</script>

<style scoped src="./DevPanel.1.css"></style>
