import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useStreamingElapsed } from './useStreamingExtractElapsed'
import { openStream, fetchFormattedFile } from './streamingExtractApi'

export function useStreamingExtractPanel(
  fileId: string,
  emit: {
    complete: (markdown: string) => void
    error: (message: string) => void
  },
) {
  const { t } = useI18n()

  // State
  const currentStage = ref('')
  const stageDetail = ref('')
  const percent = ref(0)
  const pageCount = ref(0)
  const totalChars = ref(0)
  const formulaCount = ref(0)
  const isDone = ref(false)
  const streamingMarkdown = ref('')
  const hasEmittedComplete = ref(false)

  const timeline = ref<{ label: string; duration: string; detail: string }[]>([])

  // Elapsed timer
  const { elapsedDisplay, start: startElapsed, stop: stopElapsed } = useStreamingElapsed()

  // Stage label mapping
  const stageLabels: Record<string, string> = {
    extract: 'pipeline.stage.extract',
    ocr: 'pipeline.stage.ocr',
    spans: 'pipeline.stage.spans',
    formula: 'pipeline.stage.formula',
    metadata: 'pipeline.stage.metadata',
    segment: 'pipeline.stage.segment',
    annotate: 'pipeline.stage.annotate',
    merge: 'pipeline.stage.merge',
    review: 'pipeline.stage.review',
  }

  const stageLabel = computed(() => {
    if (!currentStage.value) return t('pipeline.starting')
    return t(stageLabels[currentStage.value] || currentStage.value)
  })

  // SSE connection
  let abortController: AbortController | null = null

  function connect() {
    const token = localStorage.getItem('acacia_backend_token')
    const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860'
    const url = `${backendUrl}/extract-stream/${fileId}`

    abortController = new AbortController()
    startElapsed()

    openStream({
      url,
      headers: { Authorization: `Bearer ${token}` },
      signal: abortController.signal,
      onEvent: handleEvent,
      onError: (message) => emit.error(message),
    })
  }

  function handleEvent(event: string, data: Record<string, any>) {
    switch (event) {
      case 'pipeline_start':
        pageCount.value = data.page_count || 0
        totalChars.value = data.total_chars || 0
        break

      case 'stage_progress':
        currentStage.value = data.stage
        if (data.detail) stageDetail.value = data.detail
        if (data.percent > 0) percent.value = data.percent
        if (data.stageMs > 0 || data.totalMs > 0) {
          const dur = data.stageMs > 0 ? `${(data.stageMs / 1000).toFixed(1)}s` : ''
          timeline.value.push({
            label: t(stageLabels[data.stage] || data.stage),
            duration: dur,
            detail: data.detail || '',
          })
        }
        break

      case 'ocr_progress':
        stageDetail.value = `OCR page ${data.page}/${data.total_pages}`
        break

      case 'formula_progress':
        formulaCount.value = data.formulas_found || 0
        break

      case 'annotation_progress':
        stageDetail.value = `Sentences: ${data.sentences_done}/${data.total_sentences}`
        break

      case 'sentence_result':
        streamingMarkdown.value += data.markdown_fragment || ''
        break

      case 'review_issue':
        // Just note it in timeline
        timeline.value.push({
          label: t('pipeline.stage.review'),
          duration: '',
          detail: `${data.issue} [${data.status}]`,
        })
        break

      case 'pipeline_complete':
        isDone.value = true
        percent.value = 100
        currentStage.value = ''
        stageDetail.value = t('pipeline.complete')
        void completePipeline(typeof data.final_markdown === 'string' ? data.final_markdown : '')
        break

      case 'pipeline_error':
        if (!data.recoverable) {
          isDone.value = true
          currentStage.value = ''
          stageDetail.value = data.message
          percent.value = 0
          disconnect()
          emit.error(data.message || t('pipeline.failed'))
        }
        break
    }
  }

  function disconnect() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    stopElapsed()
  }

  async function completePipeline(finalMarkdown: string): Promise<void> {
    if (hasEmittedComplete.value) return
    hasEmittedComplete.value = true

    const formatted = await fetchFormattedFile(fileId)
    const markdown = formatted ?? finalMarkdown ?? streamingMarkdown.value
    streamingMarkdown.value = markdown
    disconnect()
    emit.complete(markdown)
  }

  onMounted(() => {
    connect()
  })

  onUnmounted(() => {
    disconnect()
  })

  return {
    stageLabel,
    elapsedDisplay,
    stageDetail,
    percent,
    isDone,
    pageCount,
    totalChars,
    formulaCount,
    timeline,
  }
}
