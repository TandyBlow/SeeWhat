<template>
  <!-- Loading (initial) -->
  <template v-if="isBusy && queueLength === 0">
    <div class="quiz-state-center">
      <div class="quiz-spinner"></div>
      <div class="quiz-state-label">加载中...</div>
    </div>
  </template>

  <!-- Error (initial) -->
  <template v-else-if="errorMessage && queueLength === 0">
    <div class="quiz-state-center">
      <div class="quiz-state-icon-circle quiz-state-error">
        <span class="quiz-state-icon">!</span>
      </div>
      <div class="quiz-state-label">{{ errorMessage }}</div>
      <div class="quiz-state-actions">
        <button class="quiz-btn-ghost" @click="$emit('start')">重试</button>
        <GlassWrapper class="quiz-btn-glass" interactive @click="$emit('back')">
          <div class="quiz-btn-glass-label">返回</div>
        </GlassWrapper>
      </div>
    </div>
  </template>

  <!-- Empty queue -->
  <template v-else-if="queueLength === 0 && !isBusy">
    <div class="quiz-state-center">
      <div class="quiz-state-icon-host">
        <GlassWrapper shape="circle">
          <div class="quiz-state-icon check">&#10003;</div>
        </GlassWrapper>
      </div>
      <div class="quiz-state-label">{{ $t('official.noDueItems') }}</div>
      <GlassWrapper class="quiz-btn-glass" interactive @click="$emit('back')">
        <div class="quiz-btn-glass-label">{{ $t('official.backToHome') }}</div>
      </GlassWrapper>
    </div>
  </template>

  <!-- Session finished -->
  <template v-else-if="sessionFinished">
    <div class="quiz-state-center">
      <div class="quiz-state-icon-host">
        <GlassWrapper shape="circle">
          <div class="quiz-state-icon check">&#10003;</div>
        </GlassWrapper>
      </div>
      <div class="quiz-state-label">{{ $t('official.sessionComplete') }}</div>
      <div class="quiz-stats">
        <div class="quiz-stat">{{ $t('official.reviewStats', { correct: sessionCorrect, total: queueLength }) }}</div>
        <div class="quiz-stat">{{ $t('official.reviewedToday', { n: queueLength }) }}</div>
      </div>
      <GlassWrapper class="quiz-btn-glass" interactive @click="$emit('back')">
        <div class="quiz-btn-glass-label">{{ $t('official.backToHome') }}</div>
      </GlassWrapper>
    </div>
  </template>
</template>

<script setup lang="ts">
import GlassWrapper from '../ui/GlassWrapper.vue'

defineProps<{
  isBusy: boolean
  queueLength: number
  errorMessage: string | null
  sessionFinished: boolean
  sessionCorrect: number
}>()

defineEmits<{
  start: []
  back: []
}>()
</script>

<style scoped src="./DailyQuizPanel.1.css"></style>
<style scoped src="./DailyQuizPanel.3.css"></style>
