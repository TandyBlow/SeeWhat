import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { AuthUser } from '../types/auth';
import { i18n } from '../i18n';
import { useGlobalLoading } from '../composables/useGlobalLoading';
import { getAuthAdapter, formatAuthError } from './authAdapter';

export type AuthMode = 'login' | 'register';

export { setAuthAdapter } from './authAdapter';

export const useAuthStore = defineStore('auth', () => {
  const { registerLoadingSource, setLoading } = useGlobalLoading();
  registerLoadingSource('authStore');

  const initialized = ref(false);
  const mode = ref<AuthMode>('login');

  const username = ref('');
  const password = ref('');
  const confirmPassword = ref('');

  const user = ref<AuthUser | null>(null);

  const isBusy = ref(false);
  const errorMessage = ref<string | null>(null);

  const isAuthenticated = computed(() => Boolean(user.value));
  const currentUsername = computed(() => {
    return user.value?.username || '';
  });
  const isRegisterMode = computed(() => mode.value === 'register');
  const canSubmit = computed(() => {
    if (isBusy.value) {
      return false;
    }
    if (username.value.length === 0 || password.value.length === 0) {
      return false;
    }
    if (!isRegisterMode.value) {
      return true;
    }
    return (
      confirmPassword.value.length > 0 &&
      confirmPassword.value === password.value
    );
  });

  function assignUser(next: AuthUser | null): void {
    if (next && next.username) {
      try { localStorage.setItem(`acacia_uname_${next.id}`, next.username); } catch (e) { console.error('[authStore] localStorage.setItem failed:', e); }
    }
    if (next && !next.username && next.id) {
      try {
        const cached = localStorage.getItem(`acacia_uname_${next.id}`);
        if (cached) {
          next = { ...next, username: cached };
        }
      } catch (e) {
        console.error('[authStore] localStorage.getItem failed:', e);
      }
    }
    if (next && !next.username && user.value?.username && user.value.id === next.id) {
      next = { ...next, username: user.value.username };
    }
    user.value = next;
  }

  function toggleMode(): void {
    mode.value = mode.value === 'login' ? 'register' : 'login';
    errorMessage.value = null;
  }

  function clearSecretsAfterSuccess(): void {
    password.value = '';
    confirmPassword.value = '';
  }

  function clearAuthFormState(): void {
    mode.value = 'login';
    username.value = '';
    password.value = '';
    confirmPassword.value = '';
  }

  async function initialize(): Promise<void> {
    const adapter = getAuthAdapter();
    if (initialized.value || !adapter) {
      initialized.value = true;
      return;
    }

    try {
      const currentUser = await adapter.initialize();
      assignUser(currentUser);
    } catch (error) {
      errorMessage.value = formatAuthError(error);
    }

    adapter.onAuthStateChange((nextUser) => {
      assignUser(nextUser);
      if (nextUser) {
        errorMessage.value = null;
      }
    });

    initialized.value = true;
  }

  async function submitByKnob(): Promise<boolean> {
    const adapter = getAuthAdapter();
    if (!adapter) {
      errorMessage.value = i18n.global.t('errors.authNotInitialized');
      return false;
    }

    if (!canSubmit.value) {
      if (isRegisterMode.value && confirmPassword.value !== password.value) {
        errorMessage.value = i18n.global.t('errors.passwordMismatch');
      }
      return false;
    }

    isBusy.value = true;
    setLoading('authStore', true);
    errorMessage.value = null;

    try {
      let result;

      if (isRegisterMode.value) {
        result = await adapter.signUp(username.value, password.value);
      } else {
        result = await adapter.signIn(username.value, password.value);
      }

      assignUser(result.user);
      clearSecretsAfterSuccess();
      return true;
    } catch (error) {
      errorMessage.value = formatAuthError(error);
      return false;
    } finally {
      isBusy.value = false;
      setLoading('authStore', false);
    }
  }

  async function logout(): Promise<boolean> {
    const adapter = getAuthAdapter();
    if (!adapter || isBusy.value) {
      return false;
    }

    const userId = user.value?.id;
    isBusy.value = true;
    setLoading('authStore', true);
    try {
      await adapter.signOut();
      if (userId) {
        try { localStorage.removeItem(`acacia_uname_${userId}`); } catch (e) { console.error('[authStore] localStorage.removeItem failed:', e); }
      }
      assignUser(null);
      clearAuthFormState();
      errorMessage.value = null;
      return true;
    } catch (e) {
      console.error('[authStore] logout failed:', e);
      return false;
    } finally {
      isBusy.value = false;
      setLoading('authStore', false);
    }
  }

  return {
    initialized,
    mode,
    username,
    password,
    confirmPassword,
    user,
    isBusy,
    errorMessage,
    isAuthenticated,
    currentUsername,
    isRegisterMode,
    canSubmit,
    initialize,
    toggleMode,
    submitByKnob,
    logout,
  };
});
