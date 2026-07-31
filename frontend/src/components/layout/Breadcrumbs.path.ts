import { ref, watch, nextTick } from 'vue';
import type { Ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n';
import { useNodeStore } from '../../stores/nodeStore';
import type { NodeRecord } from '../../types/node';

export function useBreadcrumbPath(
  crumbTrackRef: Ref<HTMLElement | null>,
  resetScroll: () => void,
) {
  const { t } = useI18n();
  const SINK_MS = 240;
  const SLIDE_MS = 280;
  const RISE_MS = 240;

  const HOME_PLACEHOLDER: NodeRecord = {
    id: '__home__',
    name: t('breadcrumbs.home'),
    content: '',
    parentId: null,
    sortOrder: 0,
  };

  const store = useNodeStore();
  const { pathNodes, activeNode } = storeToRefs(store);

  function buildFullPath(): NodeRecord[] {
    const ancestors = pathNodes.value;
    const current = activeNode.value;
    if (current) {
      // During page transitions, pathNodes may already include the current
      // node as an ancestor while activeNode hasn't been updated yet.
      // Deduplicate to avoid the same node appearing twice in the breadcrumb.
      const filtered = ancestors.filter(a => a.id !== current.id);
      return [...filtered, current];
    }
    if (ancestors.length === 0) return [HOME_PLACEHOLDER];
    return [...ancestors];
  }

  const displayNodes = ref<NodeRecord[]>(buildFullPath());
  const busy = ref(false);
  const isAnimating = ref(false);
  const slideOutIds = ref<Set<string>>(new Set());
  const enteringIds = ref<Set<string>>(new Set());
  let lastPathIds: string[] = [];

  function arraysEqual(a: string[], b: string[]): boolean {
    return a.length === b.length && a.every((v, i) => v === b[i]);
  }

  function sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async function goTo(nodeId: string): Promise<void> {
    if (busy.value) return;

    // Record navigation transition (fire-and-forget)
    const fromId = store.activeNode?.id ?? null;
    if (fromId && fromId !== nodeId) {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:7860';
      const token = localStorage.getItem('acacia_backend_token');
      fetch(`${backendUrl}/context/record-transition`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          from_node_id: fromId,
          to_node_id: nodeId,
          transition_type: 'navigation',
          reason: '',
        }),
      }).catch(() => {});
    }

    await store.loadNode(nodeId);
  }

  let animToken = 0;

  // 4-phase breadcrumb animation
  async function animateBreadcrumb(oldIds: string[], newIds: string[]) {
    if (busy.value) return;
    busy.value = true;
    isAnimating.value = true;
    const token = ++animToken;
    if (token !== animToken) return;

    const oldSet = new Set(oldIds);
    const newSet = new Set(newIds);
    const leavingIds = oldIds.filter(id => !newSet.has(id));
    const enteringIdsList = newIds.filter(id => !oldSet.has(id));

    // Phase 1: Sink — all active items → pressed (sunken)
    // isAnimating=true triggers :pressed on all GlassWrappers
    await nextTick();
    if (token !== animToken) return;
    await sleep(SINK_MS);
    if (token !== animToken) return;

    // Phase 2: Slide out — unwanted items move up behind the page
    if (leavingIds.length > 0) {
      slideOutIds.value = new Set(leavingIds);
      await sleep(SLIDE_MS);
      if (token !== animToken) return;
      slideOutIds.value = new Set();
    }

    // Commit new path to DOM
    displayNodes.value = buildFullPath();
    if (enteringIdsList.length > 0) {
      enteringIds.value = new Set(enteringIdsList);
    }

    await nextTick();
    if (token !== animToken) return;

    // Phase 3: Slide in — new items arrive from above
    if (enteringIdsList.length > 0) {
      const track = crumbTrackRef.value;
      if (track) {
        const newItems = track.querySelectorAll<HTMLElement>('.crumb-slide-in-prep');
        // Force reflow so slide-in-prep (no transition) is applied
        void track.offsetHeight;
        for (const el of newItems) {
          el.classList.remove('crumb-slide-in-prep');
          el.classList.add('crumb-slide-in');
        }
      }
      await sleep(SLIDE_MS);
      if (token !== animToken) return;

      // Clean up slide-in classes
      const track2 = crumbTrackRef.value;
      if (track2) {
        for (const el of track2.querySelectorAll<HTMLElement>('.crumb-slide-in')) {
          el.classList.remove('crumb-slide-in');
        }
      }
      enteringIds.value = new Set();
    }

    // Phase 4: Rise — all except current node regain shadow
    isAnimating.value = false;
    await nextTick();
    if (token !== animToken) return;
    await sleep(RISE_MS);
    busy.value = false;
  }

  // Watch for path changes
  watch(
    [pathNodes, activeNode],
    () => {
      const newIds = buildFullPath().map(n => n.id);

      // Initial mount or first data load — render without animation
      if (lastPathIds.length === 0) {
        displayNodes.value = buildFullPath();
        lastPathIds = newIds;
        return;
      }

      // Content-only update (e.g. rename) — update text, skip animation
      if (arraysEqual(newIds, lastPathIds)) {
        displayNodes.value = buildFullPath();
        return;
      }

      // Rapid navigation — cancel in-progress animation, snap to new state
      if (busy.value) {
        animToken++;
        slideOutIds.value = new Set();
        enteringIds.value = new Set();
        busy.value = false;
        isAnimating.value = false;
        displayNodes.value = buildFullPath();
        lastPathIds = newIds;
        return;
      }

      // Structural change — run 4-phase animation
      const oldIds = lastPathIds;
      lastPathIds = newIds;

      // Reset scroll state on path change
      resetScroll();

      animateBreadcrumb(oldIds, newIds);
    },
    { immediate: true },
  );

  return { displayNodes, slideOutIds, enteringIds, busy, isAnimating, goTo };
}
