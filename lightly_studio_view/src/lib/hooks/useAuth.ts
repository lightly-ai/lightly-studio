import { writable, derived, get } from 'svelte/store';
import { goto } from '$app/navigation';
import { browser } from '$app/environment';
import type { UserView } from '$lib/api/lightly_studio_local/types.gen';

export interface AuthState {
	user: UserView | null;
	token: string | null;
}

// Initialize auth state from localStorage if in browser
const getInitialAuthState = (): AuthState => {
	if (!browser) {
		return { user: null, token: null };
	}

	const token = localStorage.getItem('auth_token');
	const userJson = localStorage.getItem('auth_user');
	const user = userJson ? JSON.parse(userJson) : null;

	return { token, user };
};

// Create the auth store
const authState = writable<AuthState>(getInitialAuthState());

// Derived store for authentication check
const isAuthenticated = derived(authState, ($authState) => !!$authState.token);

export const useAuth = () => {
	const login = (token: string, user: UserView) => {
		if (browser) {
			localStorage.setItem('auth_token', token);
			localStorage.setItem('auth_user', JSON.stringify(user));
		}
		authState.set({ token, user });
	};

	const logout = () => {
		if (browser) {
			localStorage.removeItem('auth_token');
			localStorage.removeItem('auth_user');
		}
		authState.set({ token: null, user: null });
		goto('/login');
	};

	const getToken = (): string | null => {
		return get(authState).token;
	};

	const getUser = (): UserView | null => {
		return get(authState).user;
	};

	return {
		authState,
		isAuthenticated,
		login,
		logout,
		getToken,
		getUser
	};
};