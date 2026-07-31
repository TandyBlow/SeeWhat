import type { OfficialNodeSummary } from '../types/node';
import { apiFetch, getToken } from '../utils/api';
import type { NodeStoreState, OfficialNodeContent } from './nodeStoreState';

function getLocale(): string {
  return localStorage.getItem('acacia_locale') || 'zh-CN';
}

export interface NodeStoreRemote {
  fetchOfficialNodes(): Promise<void>;
  loadOfficialNodeContent(nodeId: string): Promise<void>;
  checkDailyQuizStatus(): Promise<void>;
}

export function createNodeStoreRemote(state: NodeStoreState): NodeStoreRemote {
  async function fetchOfficialNodes(): Promise<void> {
    try {
      state.officialNodeSummaries.value = await apiFetch<OfficialNodeSummary[]>(`/official-nodes?locale=${getLocale()}`);
    } catch (e) {
      console.error('[nodeStore] fetchOfficialNodes failed:', e);
      state.officialNodeSummaries.value = [];
    }
  }

  async function loadOfficialNodeContent(nodeId: string): Promise<void> {
    try {
      state.officialNodeContent.value = await apiFetch<OfficialNodeContent>(`/official-nodes/${nodeId}?locale=${getLocale()}`);
    } catch (e) {
      console.error('[nodeStore] loadOfficialNodeContent failed:', e);
      state.officialNodeContent.value = null;
    }
  }

  async function checkDailyQuizStatus(): Promise<void> {
    try {
      const token = getToken();
      if (!token) return;
      const backendUrl = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:7860';
      const res = await fetch(`${backendUrl}/daily-quiz/status`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        state.dailyQuizDueCount.value = data.due_count ?? 0;
      }
    } catch (e) {
      console.error('[nodeStore] checkDailyQuizStatus failed:', e);
      state.dailyQuizDueCount.value = 0;
    }
  }

  return {
    fetchOfficialNodes,
    loadOfficialNodeContent,
    checkDailyQuizStatus,
  };
}
