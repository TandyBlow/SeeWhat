import { fetchWithTimeout, backendUrl, getAuthHeaders } from './chatHttp';
import { contextChain, newLearnings } from './chatState';

export async function fetchContextChain(nodeId: string) {
  try {
    const resp = await fetchWithTimeout(
      `${backendUrl}/context/chain/${nodeId}`,
      { headers: getAuthHeaders() }
    );
    if (resp.ok) {
      const data = await resp.json();
      contextChain.value = data.chain || [];
      newLearnings.value = data.new_learnings_since_last_visit || [];
    }
  } catch (e) {
    console.error('[useNodeChat] fetchContextChain failed:', e);
  }
}

export async function recordNavigationTransition(
  fromNodeId: string | null,
  toNodeId: string,
  reason: string = ''
) {
  try {
    await fetchWithTimeout(`${backendUrl}/context/record-transition`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        from_node_id: fromNodeId,
        to_node_id: toNodeId,
        transition_type: 'navigation',
        reason,
      }),
    });
  } catch (e) {
    console.error('[useNodeChat] recordNavigationTransition failed:', e);
  }
}
