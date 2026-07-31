<template>
  <!-- file_uploaded mode: file received, show action choice -->
  <div class="file-uploaded-choice">
    <div class="choice-file-info">
      <span class="choice-file-icon">📄</span>
      <span class="choice-file-name">{{ pendingFile.filename }}</span>
      <span class="choice-file-size">{{ formatFileSize(pendingFile.size) }}</span>
    </div>
    <div class="choice-prompt">{{ $t('editor.fileUploadDone') }}</div>
    <div v-if="errorMessage" class="choice-error">{{ errorMessage }}</div>
    <div class="choice-actions">
      <div class="action-glass-host choice-glass">
        <GlassWrapper
          interactive
          @click="emit('fill')"
        >
          <div class="choice-inner">
            <span class="choice-label">{{ $t('editor.fillContent') }}</span>
            <span class="choice-desc">{{ $t('editor.fillContentDesc') }}</span>
          </div>
        </GlassWrapper>
      </div>
      <div class="action-glass-host choice-glass">
        <GlassWrapper
          interactive
          @click="emit('lineByLine')"
        >
          <div class="choice-inner">
            <span class="choice-label">{{ $t('editor.startExplain') }}</span>
            <span class="choice-desc">{{ $t('editor.startExplainDesc') }}</span>
          </div>
        </GlassWrapper>
      </div>
    </div>
    <button class="choice-cancel" @click="emit('cancel')">{{ $t('editor.cancel') }}</button>
  </div>
</template>

<script setup lang="ts">
import GlassWrapper from '../ui/GlassWrapper.vue'
import type { UploadedFile } from './MarkdownEditorContext'

defineProps<{
  pendingFile: UploadedFile
  errorMessage: string
}>()

const emit = defineEmits<{
  fill: []
  lineByLine: []
  cancel: []
}>()

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
</script>

<style scoped src="./MarkdownEditorFileChoice.1.css"></style>
