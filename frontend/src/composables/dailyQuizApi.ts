import { getToken } from '../utils/api';
import type { DueReviewItem } from '../types/node';

export interface QuizQuestion {
  id: string;
  node_id: string;
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
  question_type: 'single_choice' | 'true_false' | 'short_answer';
  difficulty: string;
  type_label: string;
}

function getBackendUrl(): string {
  return import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:7860';
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export async function fetchDailyReviewQueue(): Promise<DueReviewItem[]> {
  const url = `${getBackendUrl()}/daily-review/queue`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error((data as any).detail ?? '获取复习队列失败');
  }
  const data = await res.json();
  return data.queue ?? [];
}

export async function generateDailyQuestion(nodeId: string): Promise<QuizQuestion> {
  const url = `${getBackendUrl()}/daily-review/generate-question`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ node_id: nodeId }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error((data as any).detail ?? '生成题目失败');
  }
  return res.json();
}

export async function submitDailyAnswer(args: {
  nodeId: string;
  questionId: string;
  isCorrect: boolean;
}): Promise<void> {
  const url = `${getBackendUrl()}/submit-answer/${args.nodeId}`;
  await fetch(url, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({
      is_correct: args.isCorrect,
      question_id: args.questionId,
    }),
  });
}

export async function checkDailyQuizStatus(): Promise<{ due_count: number; today_reviewed: number; new_count: number }> {
  const url = `${getBackendUrl()}/daily-quiz/status`;
  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error((data as any).detail ?? '获取状态失败');
  }
  return res.json();
}

export async function completeDailyQuiz(): Promise<void> {
  const url = `${getBackendUrl()}/daily-quiz/complete`;
  await fetch(url, {
    method: 'POST',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
  });
}
