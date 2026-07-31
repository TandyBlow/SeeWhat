<template>
  <!-- Bottom action bar: context-sensitive -->
  <div class="bottom-actions">
    <!-- idle / text_input / file_upload: chat action buttons -->
    <template v-if="chatMode === 'idle' || chatMode === 'text_input' || chatMode === 'file_upload' || chatMode === 'file_uploaded'">
      <div class="action-glass-host">
        <GlassWrapper
          interactive
          :pressed="isChatSunk"
          @click="emit('toggleChat')"
        >
          <div class="action-inner">
            <span class="action-label">{{ $t('editor.chatGenerate') }}</span>
          </div>
        </GlassWrapper>
      </div>
      <div class="action-glass-host">
        <GlassWrapper
          interactive
          :pressed="isFileSunk"
          @click="emit('startChatFile')"
        >
          <div class="action-inner">
            <span class="action-label">{{ $t('editor.fileImport') }}</span>
          </div>
        </GlassWrapper>
      </div>
    </template>

    <!-- conversing: chat controls -->
    <template v-else-if="chatMode === 'conversing'">
      <div class="action-glass-host">
        <GlassWrapper interactive :disabled="isBusy" @click="emit('regenerate')">
          <div class="action-inner">
            <span class="action-label">{{ $t('editor.regenerate') }}</span>
          </div>
        </GlassWrapper>
      </div>
      <div class="action-glass-host">
        <GlassWrapper interactive :disabled="isBusy" @click="emit('markConcept')">
          <div class="action-inner">
            <span class="action-label">{{ $t('editor.markConcept') }}</span>
          </div>
        </GlassWrapper>
      </div>
      <div class="action-glass-host">
        <GlassWrapper interactive @click="emit('toggleChat')">
          <div class="action-inner">
            <span class="action-label">{{ $t('editor.exitChat') }}</span>
          </div>
        </GlassWrapper>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import GlassWrapper from '../ui/GlassWrapper.vue'
import type { ChatMode } from '../../composables/useNodeChat'

defineProps<{
  chatMode: ChatMode
  isBusy: boolean
  isChatSunk: boolean
  isFileSunk: boolean
}>()

const emit = defineEmits<{
  toggleChat: []
  startChatFile: []
  regenerate: []
  markConcept: []
}>()
</script>

<style scoped src="./MarkdownEditorBottomBar.1.css"></style>
