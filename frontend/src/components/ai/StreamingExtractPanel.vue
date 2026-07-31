<template>
  <div class="streaming-panel">
    <div class="stream-header">
      <span class="stream-stage-name">{{ stageLabel }}</span>
      <span class="stream-elapsed">{{ elapsedDisplay }}</span>
    </div>
    <div class="stream-stage-detail">{{ stageDetail }}</div>
    <div class="stream-bar-track">
      <div class="stream-bar-fill" :style="{ width: percent + '%' }" :class="{ done: isDone }"></div>
    </div>
    <div class="stream-stats">
      <span v-if="pageCount > 0">{{ $t('pipeline.pages', { n: pageCount }) }}</span>
      <span v-if="totalChars > 0">{{ $t('pipeline.chars', { n: totalChars }) }}</span>
      <span v-if="formulaCount > 0">{{ $t('pipeline.formulas', { n: formulaCount }) }}</span>
    </div>
    <div class="stream-timeline" v-if="timeline.length > 0">
      <div class="tl-row" v-for="(entry, i) in timeline" :key="i">
        <span class="tl-stage">{{ entry.label }}</span>
        <span class="tl-time">{{ entry.duration }}</span>
        <span class="tl-detail">{{ entry.detail }}</span>
      </div>
    </div>
    <button class="cancel-btn" @click="$emit('cancel')" v-if="!isDone">
      {{ $t('editor.cancel') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useStreamingExtractPanel } from './useStreamingExtractPanel'

const props = defineProps<{
  fileId: string
}>()

const emit = defineEmits<{
  complete: [markdown: string]
  error: [message: string]
  cancel: []
}>()

const {
  stageLabel,
  elapsedDisplay,
  stageDetail,
  percent,
  isDone,
  pageCount,
  totalChars,
  formulaCount,
  timeline,
} = useStreamingExtractPanel(props.fileId, {
  complete: (markdown: string) => emit('complete', markdown),
  error: (message: string) => emit('error', message),
})
</script>

<style scoped src="./StreamingExtractPanel.extract.css"></style>
