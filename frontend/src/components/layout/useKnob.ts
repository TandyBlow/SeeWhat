import { computed, inject, onBeforeUnmount, ref, type Ref } from 'vue';
import { storeToRefs } from 'pinia';
import { useKnobDispatch } from '../../composables/useKnobDispatch';
import { useKnobHints } from '../../composables/useKnobHints';
import { useAuthStore } from '../../stores/authStore';
import { KNOB_HOLD_MS, KNOB_DOUBLE_CLICK_MS } from '../../constants/app';

export function useKnob() {
  // Inject content animation state from MainLayout
  const contentAnimating = inject<Ref<boolean>>('contentAnimating', ref(false));

  const {
    isBusy,
    inConfirmMode,
    canConfirm,
    onHoldConfirm,
    onClick,
    onDoubleClick,
    layoutType,
  } = useKnobDispatch();

  const { recordAction, showDoubleClickHint } = useKnobHints();

  const authStore = useAuthStore();
  const { isAuthenticated } = storeToRefs(authStore);

  const isCompactLayout = computed(() => layoutType.value === 'small');

  // --- Animation state ---
  const isHolding = ref(false);
  const isClickAnimating = ref(false);

  const glassPressed = computed(() =>
    isClickAnimating.value || contentAnimating.value || isBusy.value,
  );

  const showHoldRing = computed(() =>
    inConfirmMode.value && canConfirm.value && isHolding.value,
  );

  const isInteractable = computed(() =>
    !isClickAnimating.value && !contentAnimating.value && !isBusy.value,
  );

  // --- Hint visibility ---
  // const showClickHintLocal = computed(() =>
  //   showClickHint.value && !nodeStore.isEditState,
  // );
  //
  // const showHoldHintLocal = computed(() =>
  //   showHoldHint.value && inConfirmMode.value,
  // );

  // --- Timers ---
  let holdTimer: number | null = null;
  let clickAnimTimer: number | null = null;
  let doubleClickTimer: number | null = null;
  let lastClickTime = 0;
  let triggeredByHold = false;

  // --- Click animation: sink phase (~260ms) + stay phase (~80ms) then CSS transition rises ---
  const CLICK_ANIM_MS = 420;

  function playClickAnimation(): void {
    isClickAnimating.value = true;
    if (clickAnimTimer !== null) {
      window.clearTimeout(clickAnimTimer);
    }
    clickAnimTimer = window.setTimeout(() => {
      isClickAnimating.value = false;
      clickAnimTimer = null;
    }, CLICK_ANIM_MS);
  }

  // --- Timer helpers ---
  function clearHoldTimer(): void {
    if (holdTimer !== null) {
      window.clearTimeout(holdTimer);
      holdTimer = null;
    }
  }

  function clearDblClickTimer(): void {
    if (doubleClickTimer !== null) {
      window.clearTimeout(doubleClickTimer);
      doubleClickTimer = null;
    }
    lastClickTime = 0;
  }

  // --- Press handlers ---
  function onPressStart(): void {
    if (!isInteractable.value) return;

    isHolding.value = true;
    triggeredByHold = false;
    clearHoldTimer();

    holdTimer = window.setTimeout(async () => {
      triggeredByHold = true;
      isHolding.value = false;
      clearHoldTimer();
      if (canConfirm.value) {
        playClickAnimation();
        await onHoldConfirm();
      }
    }, KNOB_HOLD_MS);
  }

  async function onPressEnd(): Promise<void> {
    if (triggeredByHold) {
      triggeredByHold = false;
      return;
    }

    if (!isHolding.value) return;

    clearHoldTimer();
    isHolding.value = false;

    if (layoutType.value === 'small') {
      const now = Date.now();
      if (now - lastClickTime < KNOB_DOUBLE_CLICK_MS && lastClickTime > 0) {
        clearDblClickTimer();
        recordAction('dblclick');
        playClickAnimation();
        await onDoubleClick();
        return;
      }

      lastClickTime = now;
      // Wait for potential second click before committing to single-click
      doubleClickTimer = window.setTimeout(async () => {
        doubleClickTimer = null;
        lastClickTime = 0;
        // recordAction('click');
        playClickAnimation();
        await onClick();
      }, KNOB_DOUBLE_CLICK_MS);
      return;
    }

    // recordAction('click');
    playClickAnimation();
    await onClick();
  }

  function onPressCancel(): void {
    if (!isHolding.value && !holdTimer && !triggeredByHold) return;
    clearHoldTimer();
    isHolding.value = false;
    triggeredByHold = false;
  }

  onBeforeUnmount(() => {
    clearHoldTimer();
    if (clickAnimTimer !== null) window.clearTimeout(clickAnimTimer);
    clearDblClickTimer();
  });

  return {
    isBusy,
    inConfirmMode,
    canConfirm,
    isAuthenticated,
    isCompactLayout,
    showDoubleClickHint,
    glassPressed,
    showHoldRing,
    onPressStart,
    onPressEnd,
    onPressCancel,
  };
}
