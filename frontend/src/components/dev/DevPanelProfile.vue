<template>
  <!-- 知识画像文本弹层 -->
  <Teleport to="body">
    <div class="dev-profile-overlay" @click.self="emit('close')">
      <div class="dev-profile-modal">
        <div class="dev-profile-header">
          <span class="dev-profile-title">{{ $t('dev.profileTitle') }}</span>
          <button class="dev-profile-close" @click="emit('close')">×</button>
        </div>
        <div class="dev-profile-body" v-if="profile">
          <div class="dev-profile-cards">
            <div class="dev-profile-card">
              <div class="dev-profile-card-label">{{ $t('dev.nodeCount') }}</div>
              <div class="dev-profile-card-value">{{ profile.nodeCount }}</div>
            </div>
            <div class="dev-profile-card">
              <div class="dev-profile-card-label">{{ $t('dev.profileTextLength') }}</div>
              <div class="dev-profile-card-value">{{ $t('upload.chars', { n: profile.profileTextLength }) }}</div>
            </div>
            <div class="dev-profile-card">
              <div class="dev-profile-card-label">{{ $t('dev.sha256Hash') }}</div>
              <div class="dev-profile-card-value dev-profile-hash">{{ profile.hashShort }}</div>
            </div>
          </div>
          <div class="dev-profile-section">
            <div class="dev-profile-section-title">{{ $t('dev.fullProfileText') }} <span class="dev-profile-hint">{{ $t('dev.profileHint') }}</span></div>
            <pre class="dev-profile-text">{{ profile.profileText }}</pre>
          </div>
          <div class="dev-profile-section">
            <div class="dev-profile-section-title">{{ $t('dev.nodeBreakdown') }} <span class="dev-profile-hint">{{ $t('dev.nodeBreakdownHint') }}</span></div>
            <table class="dev-profile-table">
              <thead>
                <tr>
                  <th class="dev-profile-th-num">#</th>
                  <th class="dev-profile-th-name">{{ $t('dev.nodeName') }}</th>
                  <th class="dev-profile-th-content">{{ $t('dev.contentPreview') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(n, i) in profile.nodes" :key="i" :class="{ 'dev-profile-empty-row': !n.hasContent }">
                  <td class="dev-profile-td-num">{{ i + 1 }}</td>
                  <td class="dev-profile-td-name">{{ n.name }}</td>
                  <td class="dev-profile-td-content">{{ n.contentPreview || $t('dev.empty') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import type { ProfileData } from './devPanelData'

defineProps<{
  profile: ProfileData | null
}>()
const emit = defineEmits<{
  close: []
}>()
</script>

<style scoped src="./DevPanelProfile.1.css"></style>
