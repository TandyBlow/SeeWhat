import { ref, computed } from 'vue';
import { useGlobalLoading } from './useGlobalLoading';
import { loadCheckpointForNode, clearCheckpointForNode } from './chatCheckpoint';
import type { ChatMessage, MentionedConcept, ChatMode } from './chatTypes';

export const mode = ref<ChatMode>('idle');
export const sessionId = ref<string | null>(null);
export const messages = ref<ChatMessage[]>([]);
export const generatedContent = ref('');
export const isBusy = ref(false);
export const errorMessage = ref('');
export const referenceText = ref('');
export const referenceFileName = ref<string | null>(null);
export const currentNodeId = ref<string | null>(null);
export const currentSubTopic = ref('');
export const totalKp = ref(1);
export const currentKpIndex = ref(0);
export const currentKpData = ref<Record<string, unknown> | null>(null);
export const isCompleted = ref(false);
export const openingMessage = ref('');
export const contextChain = ref<any[]>([]);
export const newLearnings = ref<any[]>([]);
export const mentionedConcepts = ref<MentionedConcept[]>([]);
export const markedConceptNames = ref<Set<string>>(new Set());

export const { setLoading: setGlobalLoading } = useGlobalLoading();

// ── Computed ────────────────────────────────────────────────────────

export const hasActiveConversation = computed(() =>
  sessionId.value !== null && mode.value === 'conversing'
);

export const hasResumableSession = computed(() => {
  const cp = loadCheckpointForNode(currentNodeId.value || '');
  return cp !== null && (cp.mode === 'conversing' || cp.mode === 'paused');
});

function resetChatState(modeValue?: ChatMode, nodeIdToClear?: string | null) {
  sessionId.value = null;
  messages.value = [];
  generatedContent.value = '';
  if (modeValue) mode.value = modeValue;
  errorMessage.value = '';
  referenceText.value = '';
  referenceFileName.value = null;
  currentSubTopic.value = '';
  totalKp.value = 1;
  currentKpIndex.value = 0;
  currentKpData.value = null;
  isCompleted.value = false;
  mentionedConcepts.value = [];
  markedConceptNames.value = new Set();
  if (nodeIdToClear) clearCheckpointForNode(nodeIdToClear);
}

export function resetForNewNode() {
  resetChatState();
}

export function clearChat() {
  const nodeId = currentNodeId.value;
  resetChatState('text_input', nodeId);
}

export function abandonChat() {
  const nodeId = currentNodeId.value;
  resetChatState('idle', nodeId);
}

export function setTextMode() {
  mode.value = 'text_input';
  referenceFileName.value = null;
  errorMessage.value = '';
}

export function setFileMode() {
  mode.value = 'file_upload';
  referenceText.value = '';
  errorMessage.value = '';
}

export function findLastAiMessageIndex(): number {
  const msgs = messages.value;
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i]?.role === 'ai') return i;
  }
  return -1;
}

export function _updateConcepts(data: any) {
  if (data.mentioned_concepts && Array.isArray(data.mentioned_concepts)) {
    const existing = mentionedConcepts.value;
    const existingNames = new Set(existing.map(c => c.name));
    for (const c of data.mentioned_concepts) {
      if (c.name && !existingNames.has(c.name)) {
        existingNames.add(c.name);
        existing.push({
          name: c.name,
          category: c.category || '',
          definition: c.definition || '',
          prerequisites: c.prerequisites || [],
          expansion_directions: c.expansion_directions || [],
          verified: c.verified || false,
          wiki_summary: c.wiki_summary || '',
          wiki_description: c.wiki_description || '',
        });
      }
    }
    mentionedConcepts.value = existing;
  }
}
