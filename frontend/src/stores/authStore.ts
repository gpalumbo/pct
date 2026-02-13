import { create } from 'zustand';

interface User {
  email: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('pct_token'),
  user: null,
  setAuth: (token, user) => {
    localStorage.setItem('pct_token', token);
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem('pct_token');
    set({ token: null, user: null });
  },
}));
