import { browser } from '$app/environment';

import {
    getLightlyEnterpriseSession,
    type LightlyEnterpriseSession
} from './getLightlyEnterpriseSession/getLightlyEnterpriseSession';

type UseAuthReturnType = {
    /** The authentication token from the current session */
    token?: string;
    /** The authenticated user's information including role and email */
    user?: LightlyEnterpriseSession['user'];
    /** Whether the user is currently authenticated */
    isAuthenticated: boolean;
};

/**
 * Hook to access the current authentication state.
 * Retrieves the Lightly Enterprise session from sessionStorage and provides
 * authentication status, token, and user information.
 *
 * @returns {UseAuthReturnType} Object containing authentication state
 * @returns {string} [token] - The JWT authentication token if user is authenticated
 * @returns {object} [user] - The authenticated user's information (role, email)
 * @returns {boolean} isAuthenticated - Whether the user is currently authenticated
 *
 * @example
 * const { token, user, isAuthenticated } = useAuth();
 * if (isAuthenticated) {
 *   console.log(`Logged in as ${user.email} with role ${user.role}`);
 * }
 */
export default function useAuth(): UseAuthReturnType {
    const session = getLightlyEnterpriseSession();

    return {
        token: browser ? session?.token : undefined,
        isAuthenticated: browser ? (!!session?.token) : false,
        user: browser ? session?.user : undefined
    };
}
