<template>
  <div class="dev-panel-glass">
    <div class="dev-panel-header">
      <span class="dev-panel-title">{{ $t('dev.title') }}</span>
      <button class="dev-panel-close" @click="emit('close')">−</button>
    </div>
    <div class="dev-panel-body">
      <div class="dev-toggle-row">
        <span class="dev-toggle-label">{{ $t('dev.pageTransition') }}</span>
        <button
          type="button"
          class="dev-toggle"
          :class="{ on: devStore.enableTransition }"
          @click.stop="devStore.toggleTransition()"
        >
          <span class="dev-toggle-thumb" />
        </button>
      </div>
      <div class="dev-toggle-row">
        <span class="dev-toggle-label">{{ $t('dev.manualSceneReady') }}</span>
        <button
          type="button"
          class="dev-toggle"
          :class="{ on: devStore.manualSceneReady }"
          @click.stop="devStore.toggleManualSceneReady()"
        >
          <span class="dev-toggle-thumb" />
        </button>
      </div>
      <div class="dev-toggle-row">
        <span class="dev-toggle-label">{{ $t('dev.currentStyle') }}</span>
        <span class="dev-style-name">{{ currentStyleName }}</span>
      </div>
      <div class="dev-toggle-row">
        <span class="dev-toggle-label">{{ $t('dev.language') }}</span>
        <div class="dev-lang-btns">
          <button
            class="dev-lang-btn"
            :class="{ active: locale === 'zh-CN' }"
            @click="emit('switchLocale', 'zh-CN')"
          >中文</button>
          <button
            class="dev-lang-btn"
            :class="{ active: locale === 'en-US' }"
            @click="emit('switchLocale', 'en-US')"
          >EN</button>
        </div>
      </div>
      <button
        type="button"
        class="dev-action-btn"
        :disabled="styleRegenRunning"
        @click="emit('styleRegen')"
      >
        {{ styleRegenRunning ? $t('dev.regenerating') : $t('dev.regenStyle') }}
      </button>
      <button
        type="button"
        class="dev-action-btn dev-reset-style-btn"
        @click="emit('resetStyle')"
      >
        {{ $t('dev.resetStyle') }}
      </button>
      <button
        type="button"
        class="dev-action-btn"
        :disabled="treeFadeRunning"
        @click="emit('treeFadeTest')"
      >
        {{ treeFadeRunning ? $t('dev.animating') : $t('dev.testTreeFade') }}
      </button>
      <button
        type="button"
        class="dev-action-btn dev-reset-growth-btn"
        :disabled="resetGrowthRunning"
        @click="emit('resetGrowth')"
      >
        {{ resetGrowthRunning ? $t('dev.resetting') : $t('dev.resetGrowth') }}
      </button>
      <button
        type="button"
        class="dev-action-btn dev-logout-btn"
        :disabled="logoutRunning"
        @click="emit('logout')"
      >
        {{ logoutRunning ? $t('dev.loggingOut') : $t('dev.logout') }}
      </button>
      <button
        type="button"
        class="dev-action-btn dev-profile-btn"
        :disabled="profileLoading"
        @click="emit('showProfile')"
      >
        {{ profileLoading ? $t('dev.loading') : $t('dev.viewProfile') }}
      </button>
      <div class="dev-section-label">{{ $t('dev.demoAccounts') }}</div>
      <button
        v-for="acct in DEMO_ACCOUNTS"
        :key="acct.username"
        type="button"
        class="dev-action-btn dev-demo-acct-btn"
        :disabled="demoSwitchRunning === acct.username"
        @click="emit('switchDemoAccount', acct)"
      >
        {{ demoSwitchRunning === acct.username ? $t('dev.switching') : acct.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useDevStore } from '../../stores/devStore'
import { DEMO_ACCOUNTS } from './devPanelData'
import type { DemoAccount } from './devPanelData'

defineProps<{
  currentStyleName: string
  locale: string
  styleRegenRunning: boolean
  treeFadeRunning: boolean
  resetGrowthRunning: boolean
  logoutRunning: boolean
  profileLoading: boolean
  demoSwitchRunning: string | null
}>()
const emit = defineEmits<{
  close: []
  switchLocale: [loc: string]
  styleRegen: []
  resetStyle: []
  treeFadeTest: []
  resetGrowth: []
  logout: []
  showProfile: []
  switchDemoAccount: [acct: DemoAccount]
}>()
const devStore = useDevStore()
</script>

<style scoped src="./DevPanelPanel.1.css"></style>
<style scoped src="./DevPanelPanel.2.css"></style>
