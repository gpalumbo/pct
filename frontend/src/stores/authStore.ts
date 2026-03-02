/** Auth store — Zustand with localStorage persistence. */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  email: string | null;
  isAuthenticated: boolean;
  login: (token: string, email: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      email: null,
      isAuthenticated: false,
      login: (token, email) => {
        localStorage.setItem('pct_token', token);
        set({ token, email, isAuthenticated: true });
      },
      logout: () => {
        localStorage.removeItem('pct_token');
        set({ token: null, email: null, isAuthenticated: false });
      },
    }),
    { name: 'pct-auth' },
  ),
);
