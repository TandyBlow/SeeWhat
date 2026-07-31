import type { NodeRecord } from '../types/node';
import { cloneNode } from '../utils/treeUtils';
import { LOCAL_NODES_KEY } from '../constants/app';
import { seedNodes } from './seedNodes';

export function readLocalNodes(): NodeRecord[] {
  const raw = localStorage.getItem(LOCAL_NODES_KEY);
  if (!raw) {
    localStorage.setItem(LOCAL_NODES_KEY, JSON.stringify(seedNodes));
    return seedNodes.map(cloneNode);
  }

  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed
        .filter((item) => item && typeof item.id === 'string' && typeof item.name === 'string')
        .map((item, index) => ({
          id: String(item.id),
          name: String(item.name),
          content: typeof item.content === 'string' ? item.content : '',
          parentId: item.parentId ? String(item.parentId) : null,
          sortOrder: Number.isFinite(item.sortOrder) ? Number(item.sortOrder) : index,
        }));
    }
  } catch (e) {
    console.error('[localAdapter] parse local nodes failed, using seed data:', e);
    // fallback to seed below
  }

  localStorage.setItem(LOCAL_NODES_KEY, JSON.stringify(seedNodes));
  return seedNodes.map(cloneNode);
}

export function writeLocalNodes(nodes: NodeRecord[]): void {
  localStorage.setItem(LOCAL_NODES_KEY, JSON.stringify(nodes));
}
