import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNodeStore } from '../../stores/nodeStore'
import { useDailyQuiz } from '../../composables/useDailyQuiz'

export function useDailyQuizPanel() {
  const { t } = useI18n()

  const nodeStore = useNodeStore()

  const {
    isBusy, errorMessage, currentQuestion, selectedOption, showResult,
    queue, sessionCorrect, sessionFinished,
    currentItem, progress, hasNext,
    generateQuestion, submitAnswer, selectOption, confirmSelection, reset,
    markCompleted, fetchQueue, nextQuestion,
  } = useDailyQuiz()

  const optionLabels = ['A', 'B', 'C', 'D']
  const shortAnswerText = ref('')

  const typeLabel = computed(() => {
    return currentQuestion.value?.type_label ?? '选择题'
  })

  const isCorrect = computed(() => {
    if (!currentQuestion.value) return false
    if (currentQuestion.value.question_type === 'short_answer') {
      const options = currentQuestion.value.options as unknown as { keywords?: string[] } | null
      if (options && Array.isArray(options.keywords) && options.keywords.length > 0) {
        const userLower = shortAnswerText.value.toLowerCase().trim()
        if (userLower.length === 0) return false
        return options.keywords.some((kw: string) => userLower.includes(kw.toLowerCase()))
      }
      return false
    }
    if (selectedOption.value === null) return false
    return selectedOption.value === currentQuestion.value.correct_index
  })

  const resultText = computed(() => {
    return isCorrect.value ? t('official.correct') : t('official.incorrect')
  })

  const canConfirm = computed(() => {
    if (!currentQuestion.value) return false
    if (currentQuestion.value.question_type === 'short_answer') {
      return shortAnswerText.value.trim().length > 0
    }
    return selectedOption.value !== null
  })

  function optionClasses(idx: number): Record<string, boolean> {
    return {
      selected: selectedOption.value === idx && !showResult.value,
      correct: showResult.value && idx === currentQuestion.value!.correct_index,
      wrong: showResult.value && idx === selectedOption.value && idx !== currentQuestion.value!.correct_index,
    }
  }

  function tfOptionClasses(idx: number): Record<string, boolean> {
    return {
      selected: selectedOption.value === idx && !showResult.value,
      correct: showResult.value && idx === currentQuestion.value!.correct_index,
      wrong: showResult.value && idx === selectedOption.value && idx !== currentQuestion.value!.correct_index,
    }
  }

  function onOptionClick(idx: number): void {
    if (showResult.value) return
    selectOption(idx)
  }

  async function confirmAndSubmit(): Promise<void> {
    confirmSelection()
    if (currentQuestion.value) {
      const correct = currentQuestion.value.question_type === 'short_answer'
        ? isCorrect.value
        : selectedOption.value === currentQuestion.value.correct_index
      await submitAnswer(correct)
    }
  }

  async function advanceToNext(): Promise<void> {
    shortAnswerText.value = ''
    await nextQuestion()
  }

  async function skipQuestion(): Promise<void> {
    shortAnswerText.value = ''
    await nextQuestion()
  }

  async function startSession(): Promise<void> {
    reset()
    shortAnswerText.value = ''
    await fetchQueue()
    if (queue.value.length > 0) {
      await generateQuestion()
    }
  }

  async function finishSession(): Promise<void> {
    await markCompleted()
    nodeStore.checkDailyQuizStatus()
    reset()
    shortAnswerText.value = ''
    sessionFinished.value = true
  }

  function goBack(): void {
    reset()
    shortAnswerText.value = ''
    nodeStore.checkDailyQuizStatus()
    nodeStore.onKnobClick()
  }

  onMounted(async () => {
    await fetchQueue()
    if (queue.value.length > 0) {
      await generateQuestion()
    }
  })

  return {
    isBusy,
    errorMessage,
    currentQuestion,
    showResult,
    queue,
    sessionFinished,
    sessionCorrect,
    currentItem,
    progress,
    hasNext,
    typeLabel,
    isCorrect,
    resultText,
    canConfirm,
    optionLabels,
    shortAnswerText,
    optionClasses,
    tfOptionClasses,
    startSession,
    goBack,
    finishSession,
    generateQuestion,
    skipQuestion,
    onOptionClick,
    confirmAndSubmit,
    advanceToNext,
  }
}
