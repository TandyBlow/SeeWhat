import { ref, type Ref } from 'vue';
import { getDataAdapter } from './nodeStore';
import type { StyleResult } from '../types/node';

const POLL_INTERVAL = 3000; // 3s
const POLL_MAX_MS = 360_000; // 6 min (covers 300s image + 60s LLM)

export interface GenerationController {
  generating: Ref<boolean>;
  waitForStyleGeneration(userId: string): Promise<StyleResult | null>;
}

export function createGenerationController(): GenerationController {
  const generating = ref(false);
  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let pollGeneration = 0;

  async function waitForStyleGeneration(userId: string): Promise<StyleResult | null> {
    if (pollTimer) clearTimeout(pollTimer);
    pollTimer = null;
    generating.value = true;
    const gen = ++pollGeneration;
    const deadline = Date.now() + POLL_MAX_MS;

    let pollCount = 0;
    while (Date.now() < deadline) {
      await new Promise<void>(r => {
        pollTimer = setTimeout(r, POLL_INTERVAL);
      });
      pollTimer = null;
      pollCount++;

      if (gen !== pollGeneration) return null;

      try {
        const adapter = getDataAdapter();
        const data = await adapter.fetchStyle?.(userId);
        if (data && !data.generating) {
          generating.value = false;
          return data;
        }
      } catch (e) {
        console.warn(`[styleStore] 轮询 #${pollCount} — 网络错误, 继续等待:`, e);
      }
    }

    console.warn('[styleStore] 轮询超时 — 6分钟内风格未生成完成');
    generating.value = false;
    return null;
  }

  return { generating, waitForStyleGeneration };
}
