<template>
  <div ref="panelRef" class="panel">
    <div class="activity-layout">
      <div class="activity-glass-host">
        <GlassWrapper>
          <div class="activity-scroll">
            <section v-if="viewState === ViewStates.ADD" class="block add-block">
              <h2>{{ $t('confirm.addNode') }}</h2>
              <input
                v-model="pendingNodeName"
                class="name-input"
                type="text"
                maxlength="80"
              />
              <p class="confirm-hint">{{ $t('confirm.holdKnobHint') }}</p>
            </section>

            <section v-else-if="viewState === ViewStates.DELETE" class="block delete-block">
              <h2>{{ $t('confirm.deleteNode') }}</h2>
              <div class="target-name">{{ operationNode?.name ?? '' }}</div>

              <button
                v-if="operationHasChildren"
                type="button"
                class="delete-option"
                @click="deleteWithChildren = !deleteWithChildren"
              >
                <GlassWrapper
                  class="delete-toggle"
                  shape="circle"
                  :pressed="deleteWithChildren"
                  interactive
                >
                  <span class="delete-toggle-mark">{{ deleteWithChildren ? '√' : '' }}</span>
                </GlassWrapper>
                <span class="delete-option-label">{{ $t('confirm.deleteWithChildren') }}</span>
              </button>
              <p v-if="operationHasChildren" class="delete-hint">{{ $t('confirm.deleteHint') }}</p>
            </section>
          </div>
        </GlassWrapper>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import GlassWrapper from './GlassWrapper.vue';
import { useNodeStore } from '../../stores/nodeStore';
import { usePageTransition } from '../../composables/usePageTransition';
import { ViewStates } from '../../types/node';

const nodeStore = useNodeStore();
const { viewState, pendingNodeName, operationNode, operationHasChildren, deleteWithChildren } =
  storeToRefs(nodeStore);
const { registerRegion, unregisterRegion } = usePageTransition();
const panelRef = ref<HTMLElement | null>(null);

onMounted(() => {
  registerRegion({
    id: 'content-confirm',
    type: 'glass',
    element: panelRef,
    shouldShow: (state) => {
      return state.viewState === 'add' ||
             state.viewState === 'delete' ||
             state.viewState === 'move';
    },
    parent: 'content',
  });
});

onBeforeUnmount(() => {
  unregisterRegion('content-confirm');
});
</script>

<style scoped src="./ConfirmPanel.1.css"></style>
