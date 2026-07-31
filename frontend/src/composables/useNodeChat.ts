import type { Editor } from '@tiptap/vue-3';
import {
  mode,
  sessionId,
  messages,
  generatedContent,
  isBusy,
  errorMessage,
  referenceText,
  referenceFileName,
  currentNodeId,
  currentSubTopic,
  totalKp,
  currentKpIndex,
  currentKpData,
  isCompleted,
  openingMessage,
  contextChain,
  newLearnings,
  mentionedConcepts,
  markedConceptNames,
  hasActiveConversation,
  hasResumableSession,
  resetForNewNode,
  abandonChat,
  clearChat,
  setTextMode,
  setFileMode,
} from './chatState';
import { setEditorRef, insertGeneratedContent } from './chatEditor';
import { startTextChat, startLineByLineChat, startContextualChat } from './chatStart';
import { sendMessage, skipTurn } from './chatTurn';
import { endConversation, regenerateWithTreeContext, markConcept } from './chatEnd';
import { resumeChat, resumeOrStartChat, compressAndClear } from './chatSession';
import { fetchContextChain, recordNavigationTransition } from './chatContext';
import { persistCheckpoint } from './chatCheckpoint';

export type { ChatMessage, MentionedConcept, ChatMode } from './chatTypes';

export function useNodeChat() {
  function setEditor(editor: Editor | null) {
    setEditorRef(editor);
  }

  function setNodeId(nodeId: string) {
    currentNodeId.value = nodeId;
  }

  function exitChat() {
    if (currentNodeId.value && sessionId.value) {
      persistCheckpoint({
        sessionId: sessionId.value,
        nodeId: currentNodeId.value,
        mode: 'conversing',
        timestamp: Date.now(),
      });
    }
    mode.value = 'idle';
  }

  return {
    // State
    mode,
    sessionId,
    messages,
    generatedContent,
    isBusy,
    errorMessage,
    referenceText,
    referenceFileName,
    currentNodeId,
    currentSubTopic,
    totalKp,
    currentKpIndex,
    currentKpData,
    isCompleted,
    openingMessage,
    contextChain,
    newLearnings,
    mentionedConcepts,
    markedConceptNames,
    // Computed
    hasActiveConversation,
    hasResumableSession,
    // Actions
    setEditor,
    setNodeId,
    insertGeneratedContent,
    startTextChat,
    startLineByLineChat,
    startContextualChat,
    sendMessage,
    skipTurn,
    endConversation,
    regenerateWithTreeContext,
    markConcept,
    resumeChat,
    resetForNewNode,
    abandonChat,
    clearChat,
    compressAndClear,
    exitChat,
    setTextMode,
    setFileMode,
    resumeOrStartChat,
    fetchContextChain,
    recordNavigationTransition,
  };
}
