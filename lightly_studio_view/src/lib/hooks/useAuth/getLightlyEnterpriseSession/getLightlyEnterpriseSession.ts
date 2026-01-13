import { browser } from '$app/environment';
import { AUTHENTICATION_SESSION_STORAGE_KEY } from '$lib/constants';

export const AVAILABLE_ROLES = ['admin', 'viewer'] as const;

export type Role = (typeof AVAILABLE_ROLES)[number];

export interface LightlyEnterpriseSession {
    /** JWT authentication token */
    token: string;
    /** Authenticated user information */
    user: {
        /** User's role (admin, viewer, etc.) */
        role: Role;
        /** User's email address */
        email: string;
        /** User's username */
        username: string;
    };
    /** User preferences and settings */
    settings: {
        /** Whether to show the dashboard on login */
        showDashboard: boolean;
    };
}

/**
 * Retrieves the Lightly Enterprise session from sessionStorage.
 * This function safely parses the session data stored during login.
 *
 * @returns {LightlyEnterpriseSession | null} The parsed session object or null if not found/invalid
 *
 * @example
 * const session = getLightlyEnterpriseSession();
 * if (session) {
 *   console.log(`Token: ${session.token}`);
 *   console.log(`User: ${session.user.email} (${session.user.role})`);
 * }
 */
export function getLightlyEnterpriseSession(): LightlyEnterpriseSession | null {
    if (!browser) {
        return null;
    }

    try {
        const storedData = sessionStorage.getItem(AUTHENTICATION_SESSION_STORAGE_KEY);
        if (!storedData) {
            return null;
        }
        return JSON.parse(storedData) as LightlyEnterpriseSession;
    } catch (error) {
        console.error(
            `Failed to parse ${AUTHENTICATION_SESSION_STORAGE_KEY} from sessionStorage:`,
            error
        );
        return null;
    }
}
