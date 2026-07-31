import { computed } from 'vue';
import { defineStore } from 'pinia';
import { createStyleState } from './styleState';
import { createGenerationController } from './styleGeneration';
import { createStyleActions } from './styleActions';
import { createStyleCheckActions } from './styleCheck';

export type { ThemeStyle } from './styleState';

export const useStyleStore = defineStore('style', () => {
  const state = createStyleState();
  const { generating, waitForStyleGeneration } = createGenerationController();
  const actions = createStyleActions(state, waitForStyleGeneration);
  const checkActions = createStyleCheckActions(state, waitForStyleGeneration);
  const themeClass = computed(() => '');

  return { ...state, ...actions, ...checkActions, generating, themeClass };
});
