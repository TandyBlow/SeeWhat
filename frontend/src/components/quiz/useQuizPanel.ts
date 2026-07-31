import { computed, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useNodeStore } from '../../stores/nodeStore';
import { useQuiz } from '../../composables/useQuiz';

export function useQuizPanel() {
  const nodeStore = useNodeStore();
  const { activeNode } = storeToRefs(nodeStore);

  const {
    isBusy, errorMessage, currentQuestion, selectedOption, showResult,
    generateQuestion, submitAnswer, selectOption, confirmSelection, reset,
  } = useQuiz();

  const optionLabels = ['A', 'B', 'C', 'D'];
  const shortAnswerText = ref('');
  const selectedType = ref('single_choice');

  const questionTypes = [
    { value: 'single_choice', label: '选择题' },
    { value: 'true_false', label: '判断题' },
    { value: 'short_answer', label: '简答题' },
  ];

  const typeLabel = computed(() => {
    return currentQuestion.value?.type_label ?? '选择题';
  });

  const isCorrect = computed(() => {
    if (!currentQuestion.value) return false;
    if (currentQuestion.value.question_type === 'short_answer') {
      const options = currentQuestion.value.options as unknown as { keywords?: string[] } | null;
      if (options && Array.isArray(options.keywords) && options.keywords.length > 0) {
        const userLower = shortAnswerText.value.toLowerCase().trim();
        if (userLower.length === 0) return false;
        return options.keywords.some((kw: string) => userLower.includes(kw.toLowerCase()));
      }
      return false;
    }
    if (selectedOption.value === null) return false;
    return selectedOption.value === currentQuestion.value.correct_index;
  });

  const resultText = computed(() => {
    if (!currentQuestion.value) return '';
    if (currentQuestion.value.question_type === 'short_answer') {
      return isCorrect.value ? '回答正确！关键词匹配成功' : '回答不准确，请查看参考答案';
    }
    return isCorrect.value ? '回答正确！' : '回答错误';
  });

  const canConfirm = computed(() => {
    if (!currentQuestion.value) return false;
    if (currentQuestion.value.question_type === 'short_answer') {
      return shortAnswerText.value.trim().length > 0;
    }
    return selectedOption.value !== null;
  });

  function optionClasses(idx: number): Record<string, boolean> {
    return {
      selected: selectedOption.value === idx && !showResult.value,
      correct: showResult.value && idx === currentQuestion.value!.correct_index,
      wrong: showResult.value && idx === selectedOption.value && idx !== currentQuestion.value!.correct_index,
    };
  }

  function tfOptionClasses(idx: number): Record<string, boolean> {
    return {
      selected: selectedOption.value === idx && !showResult.value,
      correct: showResult.value && idx === currentQuestion.value!.correct_index,
      wrong: showResult.value && idx === selectedOption.value && idx !== currentQuestion.value!.correct_index,
    };
  }

  function onOptionClick(idx: number): void {
    if (showResult.value) return;
    selectOption(idx);
  }

  async function confirmAndSubmit(): Promise<void> {
    confirmSelection();
    if (currentQuestion.value) {
      const correct = currentQuestion.value.question_type === 'short_answer'
        ? isCorrect.value
        : selectedOption.value === currentQuestion.value.correct_index;
      await submitAnswer(
        currentQuestion.value.node_id,
        correct,
        currentQuestion.value.id,
      );
    }
  }

  function retry(): void {
    if (activeNode.value) {
      generateQuestion(activeNode.value.id, selectedType.value);
    }
  }

  function nextQuestion(): void {
    if (activeNode.value) {
      reset();
      shortAnswerText.value = '';
      generateQuestion(activeNode.value.id, selectedType.value);
    }
  }

  function goBack(): void {
    reset();
    shortAnswerText.value = '';
    nodeStore.cancelOperation();
  }

  onMounted(() => {
    if (activeNode.value) {
      generateQuestion(activeNode.value.id, selectedType.value);
    }
  });

  return {
    activeNode,
    isBusy,
    errorMessage,
    currentQuestion,
    showResult,
    shortAnswerText,
    selectedType,
    questionTypes,
    typeLabel,
    isCorrect,
    resultText,
    canConfirm,
    optionLabels,
    optionClasses,
    tfOptionClasses,
    onOptionClick,
    confirmAndSubmit,
    retry,
    nextQuestion,
    goBack,
  };
}
