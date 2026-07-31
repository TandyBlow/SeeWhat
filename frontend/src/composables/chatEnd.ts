import { fetchWithTimeout, backendUrl, getAuthHeaders } from './chatHttp';
import { sessionId, isBusy, errorMessage, setGlobalLoading, messages, isCompleted, markedConceptNames, currentNodeId, mode, findLastAiMessageIndex, _updateConcepts } from './chatState';
import { saveCheckpoint } from './chatCheckpoint';

export async function endConversation() {
  if (!sessionId.value || isBusy.value) return;
  isBusy.value = true;
  errorMessage.value = '';
  setGlobalLoading('nodeChat', true);

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/end`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ session_id: sessionId.value }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: '结束对话失败' }));
      throw new Error(err.detail || '结束对话失败');
    }

    const data = await resp.json();
    isCompleted.value = true;

    if (data.ai_message) {
      messages.value.push({
        role: 'ai',
        content: data.ai_message,
        metadata: { action: 'end_conversation' },
      });
    }

    saveCheckpoint({ sessionId, currentNodeId, mode });
    _updateConcepts(data);
    return {
      ai_message: data.ai_message || '',
      generated_content: '',
      action: 'end_conversation',
      consolidated_content: data.consolidated_content || '',
    };
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '结束对话失败';
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}

export async function regenerateWithTreeContext(treeContext: string) {
  if (!sessionId.value || isBusy.value) return;
  isBusy.value = true;
  errorMessage.value = '';
  setGlobalLoading('nodeChat', true);

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/regenerate`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ session_id: sessionId.value, tree_context: treeContext }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: '重新生成失败' }));
      throw new Error(err.detail || '重新生成失败');
    }

    const data = await resp.json();

    // Replace last AI message
    const lastAiIdx = findLastAiMessageIndex();
    if (lastAiIdx >= 0) {
      messages.value[lastAiIdx] = {
        role: 'ai',
        content: data.ai_message,
        metadata: { action: data.action, sub_topic: data.sub_topic, regenerated: true },
      };
    } else {
      messages.value.push({
        role: 'ai',
        content: data.ai_message,
        metadata: { action: data.action, sub_topic: data.sub_topic, regenerated: true },
      });
    }

    saveCheckpoint({ sessionId, currentNodeId, mode });
    return { ai_message: data.ai_message, action: data.action, sub_topic: data.sub_topic };
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '重新生成失败';
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}

export async function markConcept(conceptName: string): Promise<{ node_id: string; name: string } | null> {
  if (!sessionId.value || isBusy.value) return null;
  isBusy.value = true;
  setGlobalLoading('nodeChat', true);

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/mark-concept`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ session_id: sessionId.value, concept_name: conceptName }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: '标记概念失败' }));
      throw new Error(err.detail || '标记概念失败');
    }

    const data = await resp.json();

    if (data.already_exists) {
      messages.value.push({
        role: 'ai',
        content: `知识点「${conceptName}」已存在于当前主题下，无需重复创建。`,
        metadata: { action: 'concept_already_exists', concept_name: conceptName },
      });
    } else {
      messages.value.push({
        role: 'ai',
        content: `已创建子节点「${conceptName}」。你可以随时离开去学习它。`,
        metadata: { action: 'concept_marked', concept_name: conceptName },
      });
    }

    const names = new Set(markedConceptNames.value);
    names.add(conceptName);
    markedConceptNames.value = names;

    return { node_id: data.node_id, name: data.name };
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '标记概念失败';
    return null;
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}
