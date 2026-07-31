<template>
  <div class="knob-panel">
    <!-- Hint columns (desktop) -->
    <!--
    <div v-if="isAuthenticated && layoutType !== 'small'" class="hint-column hint-left">
      <Transition name="cell">
        <span v-if="showClickHintLocal" class="knob-hint">{{ UI.knob.clickToHome }}</span>
      </Transition>
      <Transition name="cell">
        <span v-if="showHoldHintLocal" class="knob-hint">{{ UI.knob.holdToConfirm }}</span>
      </Transition>
    </div>
    -->

    <!-- Compact hints (mobile, stacked above) -->
    <!--
    <div v-if="isAuthenticated && isCompactLayout && (showClickHintLocal || showHoldHintLocal)" class="hint-compact hint-compact-top">
      <Transition name="cell">
        <span v-if="showClickHintLocal" class="knob-hint-compact">{{ UI.knob.clickToHome }}</span>
      </Transition>
      <Transition name="cell">
        <span v-if="showHoldHintLocal" class="knob-hint-compact">{{ UI.knob.holdToConfirm }}</span>
      </Transition>
    </div>
    -->

    <div class="knob-stage">
      <div class="knob-well">
        <div class="knob-well-inner">
          <button
            type="button"
            class="knob-hit-area"
            :class="{ confirmable: inConfirmMode && canConfirm }"
            :disabled="isBusy"
            aria-label="旋钮"
            @mousedown="onPressStart"
            @mouseup="onPressEnd"
            @mouseleave="onPressCancel"
            @touchstart.prevent="onPressStart"
            @touchend.prevent="onPressEnd"
            @touchcancel.prevent="onPressCancel"
          >
            <GlassWrapper
              class="knob-body"
              shape="circle"
              :pressed="glassPressed"
              :style="glassPressed ? 'box-shadow: inset 4px 4px 10px var(--shadow-inset-a), inset -4px -4px 10px var(--shadow-inset-b)' : undefined"
              interactive
            />
            <span v-if="showHoldRing" class="hold-ring" />
          </button>
        </div>
      </div>

      <!-- Double-click hint (small layout) -->
      <Transition name="cell">
        <span v-if="isAuthenticated && isCompactLayout && showDoubleClickHint" class="knob-dblclick-hint">{{ $t('knob.doubleClickHint') }}</span>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import GlassWrapper from '../ui/GlassWrapper.vue';
import { useKnob } from './useKnob';

const {
  isBusy, inConfirmMode, canConfirm, isAuthenticated, isCompactLayout,
  showDoubleClickHint, glassPressed, showHoldRing,
  onPressStart, onPressEnd, onPressCancel,
} = useKnob();
</script>

<style scoped src="./Knob.css"></style>
