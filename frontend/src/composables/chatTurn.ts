import { fetchWithTimeout, backendUrl, getAuthHeaders } from './chatHttp';
import { sessionId, isBusy, errorMessage, setGlobalLoading, messages, generatedContent, currentSubTopic, isCompleted, totalKp, currentKpIndex, currentKpData, currentNodeId, mode, _updateConcepts } from './chatState';
import { saveCheckpoint } from './chatCheckpoint';
import { insertGeneratedContent } from './chatEditor';

export async function sendMessage(answer: string, options?: { skipInsertContent?: boolean }) {
  if (!sessionId.value || isBusy.value) return;
  isBusy.value = true;
  errorMessage.value = '';
  setGlobalLoading('nodeChat', true);

  messages.value.push({ role: 'user', content: answer });

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/turn`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ session_id: sessionId.value, user_answer: answer }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: '对话处理失败' }));
      throw new Error(err.detail || '对话处理失败');
    }

    const data = await resp.json();

    messages.value.push({
      role: 'ai',
      content: data.ai_message,
      metadata: { action: data.action, sub_topic: data.sub_topic },
    });

    if (data.generated_content) {
      generatedContent.value += (generatedContent.value ? '\n\n' : '') + data.generated_content;
      if (!options?.skipInsertContent) {
        insertGeneratedContent(data.generated_content);
      }
    }

    if (data.sub_topic) {
      currentSubTopic.value = data.sub_topic;
    }

    if (data.completed) {
      isCompleted.value = true;
    }

    totalKp.value = data.total_kp || totalKp.value;
    currentKpIndex.value = data.current_kp_index ?? currentKpIndex.value;
    currentKpData.value = data.kp_data || currentKpData.value;

    saveCheckpoint({ sessionId, currentNodeId, mode });
    _updateConcepts(data);
    return {
      ai_message: data.ai_message,
      generated_content: data.generated_content,
      knowledge_note: data.knowledge_note || '',
      action: data.action,
      sub_topic: data.sub_topic,
      consolidated_content: data.consolidated_content || '',
      completed: data.completed || false,
    };
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '对话处理失败';
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}

export async function skipTurn() {
  if (!sessionId.value || isBusy.value) return;
  isBusy.value = true;
  errorMessage.value = '';
  setGlobalLoading('nodeChat', true);

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/turn`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ session_id: sessionId.value, user_answer: '', skip: true }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: '跳过失败' }));
      throw new Error(err.detail || '跳过失败');
    }

    const data = await resp.json();

    if (data.ai_message) {
      messages.value.push({
        role: 'ai',
        content: data.ai_message,
        metadata: { action: data.action, sub_topic: data.sub_topic },
      });
    }

    if (data.completed) {
      isCompleted.value = true;
    }

    totalKp.value = data.total_kp || totalKp.value;
    currentKpIndex.value = data.current_kp_index ?? currentKpIndex.value;
    currentKpData.value = data.kp_data || currentKpData.value;

    saveCheckpoint({ sessionId, currentNodeId, mode });
    _updateConcepts(data);
    return { ai_message: data.ai_message || '', generated_content: '', action: data.action || 'question', sub_topic: data.sub_topic || '' };
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '跳过失败';
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}
