import { browser } from '$app/environment';
import { AUTHENTICATION_SESSION_STORAGE_KEY } from '$lib/constants';
import { redirectTo } from '$lib/utils/navigation';

/**
 * Hook for handling user logout functionality.
 *
 * Clears the client-side session mirror, then does a full-page navigation to the
 * backend logout endpoint to delete the HttpOnly cookie and redirect
 * (to the control plane's logout in WorkOS mode, or the login page otherwise).
 *
 * @returns {object} Object containing the logout function
 * @returns {Function} logout - Clears the session mirror and navigates to backend logout
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

        // Clear the client-side session mirror.
        sessionStorage.removeItem(AUTHENTICATION_SESSION_STORAGE_KEY);

        // Full-page navigation to the backend logout endpoint. It deletes the HttpOnly
        // `token` cookie and redirects onward.
        redirectTo('/auth/api/v1/logout');
    };

    return {
        logout
    };
};
