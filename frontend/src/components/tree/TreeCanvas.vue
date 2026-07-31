<template>
  <div ref="containerRef" class="tree-canvas">
    <div v-if="noTreeData" class="no-tree-msg">{{ $t('tree.noBackend') }}</div>
    <div v-if="!sceneReady && !noTreeData" class="tree-loading-mask">
      <div class="tree-loading-spinner"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, toRef } from 'vue'
import { usePageTransition } from '../../composables/usePageTransition'
import { useTreeCanvasScene } from './useTreeCanvasScene'
import { useTreeCanvasSync } from './useTreeCanvasSync'

const containerRef = ref<HTMLDivElement>()
const { registerRegion, unregisterRegion } = usePageTransition()
const props = defineProps<{ visible?: boolean }>()

const scene = useTreeCanvasScene(containerRef)
const { sceneReady, noTreeData } = scene
useTreeCanvasSync(scene, toRef(props, 'visible'))

onMounted(() => {
  registerRegion({
    id: 'content-tree',
    type: 'glass',
    element: containerRef as any,
    shouldShow: (state) => {
      return state.isAuthenticated &&
             !state.activeNode &&
             state.viewState === 'display'
    },
    parent: 'content',
  })

  scene.loadIfAuthed()
})

onBeforeUnmount(() => {
  unregisterRegion('content-tree')
  scene.dispose()
})

defineExpose({
  sceneReady,
  setGrowthLevel: (gm: number, nodeCount: number, maxDepth: number) => {
    scene.setGrowthLevel(gm, nodeCount, maxDepth)
  },
  setTreeGroupScale: (s: number) => {
    scene.setTreeGroupScale(s)
  },
  transitionToParamsDirect: (params: any, durationMs: number) => {
    scene.transitionToParamsDirect(params, durationMs)
  },
  swapBackgroundTexture: (texture: any) => {
    scene.swapBackgroundTexture(texture)
  },
  getManager: () => scene.getManager(),
})
</script>

<style scoped src="./TreeCanvas.1.css"></style>
