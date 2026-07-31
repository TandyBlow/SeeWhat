import { fetchWithTimeout, backendUrl, getAuthHeaders } from './chatHttp';
import { isBusy, errorMessage, setGlobalLoading, sessionId, currentNodeId, referenceText, referenceFileName, messages, currentSubTopic, totalKp, currentKpIndex, currentKpData, mode, openingMessage, _updateConcepts } from './chatState';
import { saveCheckpoint } from './chatCheckpoint';

export async function startTextChat(nodeId: string, nodeName: string, text: string) {
  isBusy.value = true;
  errorMessage.value = '';
  setGlobalLoading('nodeChat', true);

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/start`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ node_id: nodeId, node_name: nodeName, reference_text: text }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: '启动对话失败' }));
      throw new Error(err.detail || '启动对话失败');
    }

    const data = await resp.json();
    sessionId.value = data.session_id;
    currentNodeId.value = nodeId;
    referenceText.value = text;
    referenceFileName.value = null;
    messages.value = [{
      role: 'ai',
      content: data.question,
      metadata: { action: data.action, sub_topic: data.sub_topic },
    }];
    currentSubTopic.value = data.sub_topic || '';
    totalKp.value = data.total_kp || 1;
    currentKpIndex.value = data.current_kp_index || 0;
    currentKpData.value = data.kp_data || null;
    mode.value = 'conversing';
    saveCheckpoint({ sessionId, currentNodeId, mode });
    _updateConcepts(data);
    return { question: data.question, action: data.action, sub_topic: data.sub_topic, knowledge_note: data.knowledge_note || '' };
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '启动对话失败';
    throw e;
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}

export async function startLineByLineChat(
  nodeId: string,
  nodeName: string,
  fileId: string,
  fileName: string,
  prevNodeId: string | null = null,
  transType: string = 'initial',
  transReason: string = ''
) {
  isBusy.value = true;
  errorMessage.value = '';
  setGlobalLoading('nodeChat', true);

  try {
    const body: Record<string, unknown> = {
      node_id: nodeId,
      node_name: nodeName,
      file_id: fileId,
      chat_mode: 'line_by_line',
      previous_node_id: prevNodeId,
      transition_type: transType,
      transition_reason: transReason,
    };

    const resp = await fetchWithTimeout(`${backendUrl}/chat/contextual-start`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: '启动逐句讲解失败' }));
      throw new Error(err.detail || '启动逐句讲解失败');
    }

    const data = await resp.json();
    sessionId.value = data.session_id;
    currentNodeId.value = nodeId;
    referenceFileName.value = fileName;
    openingMessage.value = data.opening_message || data.question;
    messages.value = [{
      role: 'ai',
      content: openingMessage.value,
      metadata: { action: data.action, is_opening: !!data.opening_message },
    }];
    currentSubTopic.value = data.sub_topic || '';
    totalKp.value = 1;
    currentKpIndex.value = 0;
    currentKpData.value = null;
    mode.value = 'conversing';
    saveCheckpoint({ sessionId, currentNodeId, mode });
    _updateConcepts(data);
    return { question: openingMessage.value, action: data.action };
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '启动逐句讲解失败';
    throw e;
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}

export async function startContextualChat(
  nodeId: string,
  nodeName: string,
  text: string,
  prevNodeId: string | null,
  transType: string,
  transReason: string
) {
  isBusy.value = true;
  errorMessage.value = '';
  setGlobalLoading('nodeChat', true);

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/contextual-start`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        node_id: nodeId,
        node_name: nodeName,
        reference_text: text,
        previous_node_id: prevNodeId,
        transition_type: transType,
        transition_reason: transReason,
      }),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: '启动对话失败' }));
      throw new Error(err.detail || '启动对话失败');
    }

    const data = await resp.json();
    sessionId.value = data.session_id;
    currentNodeId.value = nodeId;
    referenceText.value = text;
    referenceFileName.value = null;
    openingMessage.value = data.opening_message || data.question;

    messages.value = [{
      role: 'ai',
      content: openingMessage.value,
      metadata: {
        action: data.opening_action || data.action,
        sub_topic: data.opening_sub_topic || data.sub_topic,
        is_opening: true,
      },
    }];
    currentSubTopic.value = data.opening_sub_topic || data.sub_topic || '';
    totalKp.value = data.total_kp || 1;
    currentKpIndex.value = data.current_kp_index || 0;
    currentKpData.value = data.kp_data || null;
    mode.value = 'conversing';
    saveCheckpoint({ sessionId, currentNodeId, mode });
    _updateConcepts(data);
    return {
      question: openingMessage.value,
      action: data.action,
      sub_topic: currentSubTopic.value,
      knowledge_note: data.knowledge_note || '',
    };
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : '启动对话失败';
    throw e;
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}
