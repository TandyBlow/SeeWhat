<template>
  <div ref="treeRef" class="tree-shell">
    <div class="tree-header">
      <h2>{{ $t('tree.treeOverview') }}</h2>
      <p class="tree-hint">{{ $t('tree.dragHint') }}</p>
    </div>

    <div ref="rootZoneRef" class="root-zone" data-sortable data-parent-id="">
      <span class="root-zone-hint">{{ $t('tree.dragToRoot') }}</span>
    </div>

    <div ref="scrollRef" class="tree-scroll">
      <ul ref="rootListRef" class="tree-root" data-sortable data-parent-id="">
        <TreeNodeItem
          v-for="node in treeNodes"
          :key="node.id"
          :node="node"
          :depth="0"
          :expanded-ids="expandedIds"
          :selected-parent-id="null"
          :blocked-parent-ids="[]"
          @toggle="toggleExpand"
          @select="handleNodeSelect"
        />
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import TreeNodeItem from './TreeNodeItem.vue'
import { useNodeStore } from '../../stores/nodeStore'
import { usePageTransition } from '../../composables/usePageTransition'
import { useTextAutoContrast } from '../../composables/useTextAutoContrast'
import { collectAllIds } from './treeOverviewUtil'
import { useTreeOverviewSortable } from './useTreeOverviewSortable'

const store = useNodeStore()
const { treeNodes } = storeToRefs(store)
const { registerRegion, unregisterRegion } = usePageTransition()
const treeRef = ref<HTMLElement | null>(null)
const rootZoneRef = ref<HTMLElement | null>(null)
const rootListRef = ref<HTMLElement | null>(null)
const scrollRef = ref<HTMLElement | null>(null)
useTextAutoContrast(scrollRef, '.node-btn, .expand-btn')
const expandedIds = ref<string[]>([])

const { initSortables, destroySortables, wasDragging } = useTreeOverviewSortable({
  treeRef,
  rootZoneRef,
  treeNodes,
})

function toggleExpand(id: string): void {
  if (expandedIds.value.includes(id)) {
    expandedIds.value = expandedIds.value.filter((item) => item !== id)
    return
  }
  expandedIds.value = [...expandedIds.value, id]
}

function handleNodeSelect(nodeId: string): void {
  if (wasDragging.value) {
    wasDragging.value = false
    return
  }
  store.loadNode(nodeId)
}

watch(
  treeNodes,
  () => {
    const ids: string[] = []
    collectAllIds(treeNodes.value, ids)
    expandedIds.value = ids
  },
  { immediate: true },
)

watch([treeNodes, expandedIds], async () => {
  await nextTick()
  initSortables()
}, { flush: 'post' })

onMounted(async () => {
  void rootListRef
  registerRegion({
    id: 'content-treeoverview',
    type: 'glass',
    element: treeRef,
    shouldShow: (state) => state.viewState === 'tree_overview',
    parent: 'content',
  })

  if (treeNodes.value.length === 0) {
    await store.refreshTree()
  }
  await nextTick()
  initSortables()
})

onBeforeUnmount(() => {
  destroySortables()
  unregisterRegion('content-treeoverview')
})
</script>

<style scoped src="./TreeOverview.1.css"></style>
