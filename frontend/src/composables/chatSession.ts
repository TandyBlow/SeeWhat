import { fetchWithTimeout, backendUrl, getAuthHeaders } from './chatHttp';
import { sessionId, isBusy, setGlobalLoading, currentNodeId, messages, generatedContent, totalKp, currentKpIndex, currentKpData, mode, clearChat } from './chatState';
import { loadCheckpointForNode, saveCheckpoint, clearCheckpointForNode } from './chatCheckpoint';

export async function resumeChat(nodeId: string): Promise<boolean> {
  const cp = loadCheckpointForNode(nodeId);
  if (!cp) return false;

  isBusy.value = true;
  setGlobalLoading('nodeChat', true);

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/sessions/${cp.sessionId}`, {
      headers: getAuthHeaders(),
    });
    if (!resp.ok) {
      clearCheckpointForNode(nodeId);
      return false;
    }

    const data = await resp.json();
    sessionId.value = data.session_id;
    currentNodeId.value = nodeId;
    messages.value = data.messages || [];
    generatedContent.value = data.generated_content || '';
    totalKp.value = data.total_kp || 1;
    currentKpIndex.value = data.current_kp_index || 0;
    currentKpData.value = data.kp_data || null;
    mode.value = 'conversing';
    return true;
  } catch (e) {
    console.error('[useNodeChat] resumeChat failed:', e);
    clearCheckpointForNode(nodeId);
    return false;
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}

export async function resumeOrStartChat(): Promise<boolean> {
  if (currentNodeId.value) {
    const cp = loadCheckpointForNode(currentNodeId.value);
    if (cp && cp.mode === 'conversing') {
      const success = await resumeChat(currentNodeId.value);
      if (success) return true;
    }

    try {
      const resp = await fetchWithTimeout(
        `${backendUrl}/chat/sessions/by-node/${currentNodeId.value}`,
        { headers: getAuthHeaders() }
      );
      if (resp.ok) {
        const data = await resp.json();
        if (data.session_id) {
          sessionId.value = data.session_id;
          saveCheckpoint({ sessionId, currentNodeId, mode });
          const success = await resumeChat(currentNodeId.value);
          if (success) return true;
        }
      }
    } catch (e) {
      console.error('[useNodeChat] resumeOrStartChat session lookup failed:', e);
    }
  }

  return false;
}

export async function compressAndClear(): Promise<string> {
  const sid = sessionId.value;
  if (!sid) {
    clearChat();
    return '';
  }

  isBusy.value = true;
  setGlobalLoading('nodeChat', true);

  try {
    const resp = await fetchWithTimeout(`${backendUrl}/chat/compress`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ session_id: sid }),
    });

    if (!resp.ok) {
      // If compression fails (e.g. too few messages), just clear without compression
      clearChat();
      return '';
    }

    const data = await resp.json();
    clearChat();
    return data.summary || '';
  } catch (e) {
    console.error('[useNodeChat] compressAndClear failed:', e);
    // On any error, fallback to plain clear
    clearChat();
    return '';
  } finally {
    isBusy.value = false;
    setGlobalLoading('nodeChat', false);
  }
}
