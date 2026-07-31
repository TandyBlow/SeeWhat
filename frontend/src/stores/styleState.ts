import { ref, type Ref } from 'vue';

export type ThemeStyle = string;

export interface StyleState {
  style: Ref<ThemeStyle>;
  styleParams: Ref<Record<string, unknown> | null>;
  backgroundUrl: Ref<string | null>;
  distribution: Ref<Record<string, number>>;
  loaded: Ref<boolean>;
  pendingParams: Ref<Record<string, unknown> | null>;
  pendingStyle: Ref<ThemeStyle>;
  pendingBackgroundUrl: Ref<string | null>;
  isPendingReady: Ref<boolean>;
  styleLocked: Ref<boolean>;
}

export function createStyleState(): StyleState {
  return {
    style: ref<ThemeStyle>('default'),
    styleParams: ref<Record<string, unknown> | null>(null),
    backgroundUrl: ref<string | null>(null),
    distribution: ref<Record<string, number>>({}),
    loaded: ref(false),
    pendingParams: ref<Record<string, unknown> | null>(null),
    pendingStyle: ref<ThemeStyle>('default'),
    pendingBackgroundUrl: ref<string | null>(null),
    isPendingReady: ref(false),
    styleLocked: ref(false),
  };
}
