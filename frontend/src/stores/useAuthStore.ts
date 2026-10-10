// src/stores/useAuthStore.ts
import { create, persist } from './zustand-lite';

export type UserRole = 'candidate' | 'employer' | 'admin' | 'public';

export interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  role: UserRole;
  userId: number | null;
  email: string | null;
  isPdnConsentGiven: boolean;
  isProfilePublicationConsentGiven: boolean;
  setAuthSession: (token: string, refresh: string, role: UserRole, userId: number, email: string) => void;
  setConsents: (pdn: boolean, pub: boolean) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      role: 'public',
      userId: null,
      email: null,
      isPdnConsentGiven: false,
      isProfilePublicationConsentGiven: false,
      setAuthSession: (accessToken, refreshToken, role, userId, email) =>
        set({ accessToken, refreshToken, role, userId, email }),
      setConsents: (isPdnConsentGiven, isProfilePublicationConsentGiven) =>
        set({ isPdnConsentGiven, isProfilePublicationConsentGiven }),
      clearAuth: () =>
        set({
          accessToken: null,
          refreshToken: null,
          role: 'public',
          userId: null,
          email: null,
          isPdnConsentGiven: false,
          isProfilePublicationConsentGiven: false,
        }),
    }),
    { name: 'fsp_auth_storage' }
  )
);
