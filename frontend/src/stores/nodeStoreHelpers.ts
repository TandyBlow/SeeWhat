import type { NodeRecord, TreeNode, ViewState } from '../types/node';
import { ViewStates } from '../types/node';
import { findTreeNode, collectTreeDescendantIds } from '../utils/treeUtils';

export function computeHasAnyNodes(
  nodeInfo: NodeRecord | null,
  children: NodeRecord[],
  pathNodes: NodeRecord[],
): boolean {
  return !!(nodeInfo || children.length > 0 || pathNodes.length > 0);
}

export function computeIsEditState(viewState: ViewState): boolean {
  return (
    viewState === ViewStates.ADD ||
    viewState === ViewStates.MOVE ||
    viewState === ViewStates.DELETE
  );
}

export function computeCanConfirm(
  viewState: ViewState,
  pendingNodeName: string,
  operationNode: NodeRecord | null,
  moveTargetParentId: string | null,
  blockedParentIds: string[],
): boolean {
  if (viewState === ViewStates.ADD) {
    return pendingNodeName.trim().length > 0;
  }
  if (viewState === ViewStates.DELETE) {
    return Boolean(operationNode);
  }
  if (viewState === ViewStates.MOVE) {
    if (!operationNode) {
      return false;
    }
    if (moveTargetParentId === operationNode.parentId) {
      return false;
    }
    if (!moveTargetParentId) {
      return true;
    }
    return !blockedParentIds.includes(moveTargetParentId);
  }
  return false;
}

export function buildBlockedParentIds(treeNodes: TreeNode[], nodeId: string): string[] {
  const hit = findTreeNode(treeNodes, nodeId);
  const blocked = new Set<string>([nodeId]);
  collectTreeDescendantIds(hit, blocked);
  return Array.from(blocked);
}
