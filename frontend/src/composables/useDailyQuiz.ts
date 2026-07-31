import { ref, computed } from 'vue';
import type { DueReviewItem } from '../types/node';
import {
  checkDailyQuizStatus,
  completeDailyQuiz,
  fetchDailyReviewQueue,
  generateDailyQuestion,
  submitDailyAnswer,
} from './dailyQuizApi';
import type { QuizQuestion } from './dailyQuizApi';

export type { QuizQuestion } from './dailyQuizApi';

export function useDailyQuiz() {
  // Queue state
  const queue = ref<DueReviewItem[]>([]);
  const currentIndex = ref(0);
  const sessionCorrect = ref(0);
  const sessionFinished = ref(false);

  // Question state (reused from existing)
  const isBusy = ref(false);
  const errorMessage = ref<string | null>(null);
  const currentQuestion = ref<QuizQuestion | null>(null);
  const selectedOption = ref<number | null>(null);
  const showResult = ref(false);

  // Computed
  const currentItem = computed<DueReviewItem | null>(() => {
    if (currentIndex.value < queue.value.length) {
      return queue.value[currentIndex.value] ?? null;
    }
    return null;
  });

  const progress = computed(() => {
    const total = queue.value.length;
    const current = currentIndex.value;
    return {
      current: total > 0 ? current + 1 : 0,
      total,
      percent: total > 0 ? Math.round(((current) / total) * 100) : 0,
    };
  });

  const hasNext = computed(() => {
    return currentIndex.value < queue.value.length - 1;
  });

  // Fetch review queue
  async function fetchQueue(): Promise<void> {
    isBusy.value = true;
    errorMessage.value = null;
    try {
      queue.value = await fetchDailyReviewQueue();
      currentIndex.value = 0;
      sessionCorrect.value = 0;
      sessionFinished.value = false;
    } catch (error: unknown) {
      errorMessage.value = error instanceof Error ? error.message : '获取复习队列失败';
    } finally {
      isBusy.value = false;
    }
  }

  // Generate question for current node in queue
  async function generateQuestion(): Promise<void> {
    const item = currentItem.value;
    if (!item) return;

    isBusy.value = true;
    errorMessage.value = null;
    currentQuestion.value = null;
    selectedOption.value = null;
    showResult.value = false;

    try {
      currentQuestion.value = await generateDailyQuestion(item.node_id);
    } catch (error: unknown) {
      errorMessage.value = error instanceof Error ? error.message : '生成题目失败';
    } finally {
      isBusy.value = false;
    }
  }

  // Submit answer for current question
  async function submitAnswer(isCorrect: boolean): Promise<void> {
    if (!currentQuestion.value) return;
    try {
      await submitDailyAnswer({
        nodeId: currentQuestion.value.node_id,
        questionId: currentQuestion.value.id,
        isCorrect,
      });
      if (isCorrect) {
        sessionCorrect.value++;
      }
    } catch (e) {
      console.error('[useDailyQuiz] submitAnswer failed:', e);
    }
  }

  // Move to next item and generate its question
  async function nextQuestion(): Promise<void> {
    if (hasNext.value) {
      currentIndex.value++;
      await generateQuestion();
    } else {
      // Queue exhausted
      sessionFinished.value = true;
    }
  }

  // Check daily review status (due count)
  async function checkStatus(): Promise<{ due_count: number; today_reviewed: number; new_count: number }> {
    return checkDailyQuizStatus();
  }

  // Mark daily session complete (optional, for backward compat)
  async function markCompleted(): Promise<void> {
    try {
      await completeDailyQuiz();
    } catch (e) {
      console.error('[useDailyQuiz] markCompleted failed:', e);
    }
  }

  function selectOption(idx: number): void {
    if (showResult.value) return;
    selectedOption.value = idx;
  }

  function confirmSelection(): void {
    showResult.value = true;
  }

  function reset(): void {
    currentQuestion.value = null;
    selectedOption.value = null;
    showResult.value = false;
    errorMessage.value = null;
    queue.value = [];
    currentIndex.value = 0;
    sessionCorrect.value = 0;
    sessionFinished.value = false;
  }

  return {
    // Queue
    queue,
    currentIndex,
    sessionCorrect,
    sessionFinished,
    currentItem,
    progress,
    hasNext,
    fetchQueue,
    nextQuestion,
    // Question
    isBusy,
    errorMessage,
    currentQuestion,
    selectedOption,
    showResult,
    generateQuestion,
    submitAnswer,
    markCompleted,
    selectOption,
    confirmSelection,
    checkStatus,
    reset,
  };
}
