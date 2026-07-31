import type { Ref } from 'vue';
import type { ChatMode, ChatCheckpoint, CheckpointMap } from './chatTypes';

const CHECKPOINT_MAP_KEY = 'acacia_chat_checkpoint_map_v1';
const MAX_CHECKPOINT_ENTRIES = 50;

export function saveCheckpoint(state: { sessionId: Ref<string | null>; currentNodeId: Ref<string | null>; mode: Ref<ChatMode> }) {
  const sid = state.sessionId.value;
  const cid = state.currentNodeId.value;
  if (!sid || !cid) return;
  const checkpoint: ChatCheckpoint = {
    sessionId: sid,
    nodeId: cid,
    mode: state.mode.value,
    timestamp: Date.now(),
  };
  try {
    const map = loadCheckpointMap();
    map[cid] = checkpoint;
    const entries = Object.entries(map);
    if (entries.length > MAX_CHECKPOINT_ENTRIES) {
      entries.sort((a, b) => b[1].timestamp - a[1].timestamp);
      const trimmed: CheckpointMap = {};
      entries.slice(0, MAX_CHECKPOINT_ENTRIES).forEach(([k, v]) => trimmed[k] = v);
      localStorage.setItem(CHECKPOINT_MAP_KEY, JSON.stringify(trimmed));
    } else {
      localStorage.setItem(CHECKPOINT_MAP_KEY, JSON.stringify(map));
    }
  } catch (e) {
    console.error('[useNodeChat] saveCheckpointMap failed:', e);
  }
}

export function loadCheckpointMap(): CheckpointMap {
  try {
    const raw = localStorage.getItem(CHECKPOINT_MAP_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    console.error('[useNodeChat] loadCheckpointMap failed');
    return {};
  }
}

export function loadCheckpointForNode(nodeId: string): ChatCheckpoint | null {
  const map = loadCheckpointMap();
  return map[nodeId] || null;
}

export function clearCheckpointForNode(nodeId: string) {
  const map = loadCheckpointMap();
  delete map[nodeId];
  localStorage.setItem(CHECKPOINT_MAP_KEY, JSON.stringify(map));
}

export function persistCheckpoint(checkpoint: ChatCheckpoint) {
  try {
    const map = loadCheckpointMap();
    map[checkpoint.nodeId] = checkpoint;
    localStorage.setItem(CHECKPOINT_MAP_KEY, JSON.stringify(map));
  } catch (e) {
    console.error('[useNodeChat] saveCheckpoint (checkpoint) failed:', e);
  }
}
