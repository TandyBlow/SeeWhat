import { computed, onMounted, ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useNodeStore } from '../../stores/nodeStore';
import { useQuiz } from '../../composables/useQuiz';
import type { QuizQuestionListItem, QuizQuestion } from '../../composables/useQuiz';
import { apiFetch } from '../../utils/api';

export function useQuizPanel() {
  const nodeStore = useNodeStore();
  const { activeNode } = storeToRefs(nodeStore);

  const {
    isBusy, errorMessage,
    questions: nodeQuestions, wrongQuestions,
    fetchQuestions, fetchWrongQuestions, submitAnswer,
  } = useQuiz();

  const tab = ref<'node' | 'wrong'>('node');

  // Inline quiz state
  const activeQuestion = ref<QuizQuestion | null>(null);
  const quizSelectedOption = ref<number | null>(null);
  const quizShowResult = ref(false);
  const quizShortAnswer = ref('');

  const optionLabels = ['A', 'B', 'C', 'D'];

  const wrongList = computed(() => wrongQuestions.value);

  const displayList = computed(() => {
    if (tab.value === 'node') return nodeQuestions.value;
    return wrongList.value;
  });

  const quizIsCorrect = computed(() => {
    if (!activeQuestion.value) return false;
    if (activeQuestion.value.question_type === 'short_answer') return true;
    if (quizSelectedOption.value === null) return false;
    return quizSelectedOption.value === activeQuestion.value.correct_index;
  });

  const quizResultText = computed(() => {
    if (!activeQuestion.value) return '';
    if (activeQuestion.value.question_type === 'short_answer') {
      return '简答题——请对照参考答案自行评估';
    }
    return quizIsCorrect.value ? '回答正确！' : '回答错误';
  });

  const quizCanConfirm = computed(() => {
    if (!activeQuestion.value) return false;
    if (activeQuestion.value.question_type === 'short_answer') {
      return quizShortAnswer.value.trim().length > 0;
    }
    return quizSelectedOption.value !== null;
  });

  function hasResult(q: QuizQuestionListItem | QuizQuestion): boolean {
    return 'answered' in q && q.answered;
  }

  function getResult(q: QuizQuestionListItem | QuizQuestion) {
    return q as QuizQuestionListItem;
  }

  function quizOptionClasses(idx: number): Record<string, boolean> {
    return {
      selected: quizSelectedOption.value === idx && !quizShowResult.value,
      correct: quizShowResult.value && idx === activeQuestion.value!.correct_index,
      wrong: quizShowResult.value && idx === quizSelectedOption.value && idx !== activeQuestion.value!.correct_index,
    };
  }

  function quizTfClasses(idx: number): Record<string, boolean> {
    return {
      selected: quizSelectedOption.value === idx && !quizShowResult.value,
      correct: quizShowResult.value && idx === activeQuestion.value!.correct_index,
      wrong: quizShowResult.value && idx === quizSelectedOption.value && idx !== activeQuestion.value!.correct_index,
    };
  }

  function onQuizOptionClick(idx: number): void {
    if (quizShowResult.value) return;
    quizSelectedOption.value = idx;
  }

  async function openQuestion(q: QuizQuestionListItem | QuizQuestion): Promise<void> {
    try {
      // Fetch full question with correct_index (not exposed in list)
      const full = await apiFetch<QuizQuestion>(`/quiz-questions/${q.node_id || activeNode.value?.id}/${q.id}`);
      activeQuestion.value = full;
      quizSelectedOption.value = null;
      quizShowResult.value = false;
      quizShortAnswer.value = '';
    } catch (e) {
      console.error('[QuizHistoryPanel] fetchQuestionDetail failed:', e);
      // If fetch fails, try to use what we have
    }
  }

  async function confirmQuizAnswer(): Promise<void> {
    quizShowResult.value = true;
    if (activeQuestion.value) {
      const correct = activeQuestion.value.question_type === 'short_answer'
        ? true
        : quizSelectedOption.value === activeQuestion.value.correct_index;
      await submitAnswer(
        activeQuestion.value.node_id,
        correct,
        activeQuestion.value.id,
      );
    }
  }

  function switchTab(t: 'node' | 'wrong'): void {
    tab.value = t;
    activeQuestion.value = null;
    refresh();
  }

  function refresh(): void {
    if (tab.value === 'node' && activeNode.value) {
      fetchQuestions(activeNode.value.id);
    } else if (tab.value === 'wrong') {
      fetchWrongQuestions();
    }
  }

  function goBack(): void {
    activeQuestion.value = null;
    nodeStore.cancelOperation();
  }

  onMounted(() => {
    if (activeNode.value) {
      fetchQuestions(activeNode.value.id);
    }
  });

  return {
    tab,
    activeNode,
    isBusy,
    errorMessage,
    nodeQuestions,
    wrongList,
    displayList,
    activeQuestion,
    quizShowResult,
    quizShortAnswer,
    quizIsCorrect,
    quizResultText,
    quizCanConfirm,
    optionLabels,
    hasResult,
    getResult,
    quizOptionClasses,
    quizTfClasses,
    onQuizOptionClick,
    openQuestion,
    confirmQuizAnswer,
    switchTab,
    refresh,
    goBack,
  };
}
