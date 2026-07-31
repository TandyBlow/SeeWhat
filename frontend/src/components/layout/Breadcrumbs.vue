<template>
  <div class="breadcrumbs-shell">
    <div
      v-if="isAuthenticated"
      class="crumb-track"
      ref="crumbTrackRef"
      @wheel.passive="onWheel"
      @touchstart.passive="onTouchStart"
      @touchmove.passive="onTouchMove"
      @touchend.passive="onTouchEnd"
    >
      <GlassWrapper
        v-for="(node, i) in displayNodes"
        :key="node.id"
        class="crumb-wrap"
        :class="{
          'current-wrap': i === displayNodes.length - 1,
          'crumb-slide-out': slideOutIds.has(node.id),
          'crumb-slide-in-prep': enteringIds.has(node.id),
        }"
        :data-crumb-id="node.id"
        :pressed="i === displayNodes.length - 1 || isAnimating"
        interactive
        @click="i < displayNodes.length - 1 && !busy && goTo(node.id)"
      >
        <component
          :is="i === displayNodes.length - 1 ? 'div' : 'button'"
          :class="i === displayNodes.length - 1 ? 'current-node' : 'crumb'"
          :type="i === displayNodes.length - 1 ? undefined : 'button'"
        >
          {{ node.name }}
        </component>
      </GlassWrapper>
    </div>

    <div v-else class="crumb-track">
      <GlassWrapper class="crumb-wrap current-wrap" pressed>
        <div class="current-node">
          {{ $t('breadcrumbs.welcome') }}
        </div>
      </GlassWrapper>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { storeToRefs } from 'pinia';
import GlassWrapper from '../ui/GlassWrapper.vue';
import { useAuthStore } from '../../stores/authStore';
import { useBreadcrumbScroll } from './Breadcrumbs.scroll';
import { useBreadcrumbPath } from './Breadcrumbs.path';

const { isAuthenticated } = storeToRefs(useAuthStore());

const crumbTrackRef = ref<HTMLElement | null>(null);

const { onWheel, onTouchStart, onTouchMove, onTouchEnd, resetScroll } =
  useBreadcrumbScroll(crumbTrackRef);

const { displayNodes, slideOutIds, enteringIds, busy, isAnimating, goTo } =
  useBreadcrumbPath(crumbTrackRef, resetScroll);
</script>

<style scoped src="./Breadcrumbs.1.css"></style>

<style scoped src="./Breadcrumbs.2.css"></style>
