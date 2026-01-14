import { browser } from '$app/environment';
import { AUTHENTICATION_SESSION_STORAGE_KEY } from '$lib/constants';
import { goto } from '$app/navigation';

/**
 * Hook for handling user logout functionality.
 * Clears the authentication session from sessionStorage, clears the auth cookie, and redirects to the login page.
 *
 * @returns {object} Object containing the logout function
 * @returns {Function} logout - Function that clears session, cookie and redirects to login
 *
 * @example
 * const { logout } = useLogout();
 *
 * // Trigger logout
 * logout();
 */
export const useLogout = () => {
    const logout = function () {
        if (!browser) return;

        // Clear session storage
        sessionStorage.removeItem(AUTHENTICATION_SESSION_STORAGE_KEY);

        // Clear authentication cookie
        document.cookie = 'token=; path=/; max-age=0';

        // redirect to login page
        goto('/workspace/login');
    };

    return {
        logout
    };
};
