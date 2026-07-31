<template>
  <!-- @deprecated conversing textarea mode: 当前交互流程中用户始终走 text_input 内联模式，
       这个 textarea 只在 API 请求期间短暂闪现，实际不会被用到。修改 AI 对话功能时请改 sendInlineMessage()。 -->
  <div class="conversation-input-area">
    <div class="conv-progress">
      <span class="conv-progress-label">
        <template v-if="totalKp <= 1">
          {{ isCompleted ? $t('editor.chatEnded') : $t('editor.chatting') }}
        </template>
        <template v-else>
          {{ $t('editor.kpProgress', { current: currentKpIndex + 1, total: totalKp }) }}
        </template>
      </span>
      <span v-if="currentSubTopic" class="conv-progress-topic">{{ currentSubTopic }}</span>
      <div class="conv-progress-track">
        <div
          class="conv-progress-fill"
          :class="{ 'conv-progress-indeterminate': totalKp <= 1 && !isCompleted }"
          :style="totalKp > 1 || isCompleted ? { width: progressPercent + '%' } : {}"
        />
      </div>
    </div>

    <textarea
      v-model="userInput"
      class="conv-textarea"
      :placeholder="$t('editor.inputPlaceholder')"
      :disabled="isBusy || isCompleted"
      rows="3"
      @keydown="onKeydown"
    />

    <div class="conv-actions">
      <button
        class="conv-btn conv-btn-skip"
        :disabled="isBusy || isCompleted"
        @click="emit('skip')"
      >{{ $t('editor.skip') }}</button>
      <button
        class="conv-btn conv-btn-end"
        :disabled="isBusy || isCompleted"
        @click="emit('end')"
      >{{ $t('editor.endChat') }}</button>
      <button
        class="conv-btn conv-btn-send"
        :disabled="!canSend || isBusy || isCompleted"
        @click="emit('send')"
      >
        {{ isBusy ? $t('editor.sending') : $t('editor.send') }}
      </button>
    </div>

    <div v-if="isCompleted" class="conv-completed-banner">
      {{ $t('editor.chatEndedHint') }}
    </div>
  </div>
</template>

<script setup lang="ts">
const userInput = defineModel<string>('userInput')

defineProps<{
  totalKp: number
  currentKpIndex: number
  isCompleted: boolean
  currentSubTopic: string | null
  isBusy: boolean
  canSend: boolean
  progressPercent: number
}>()

const emit = defineEmits<{
  convKeydown: [event: KeyboardEvent]
  skip: []
  end: []
  send: []
}>()

function onKeydown(event: KeyboardEvent) {
  emit('convKeydown', event)
}
</script>

<style scoped src="./MarkdownEditorConversing.1.css"></style>
