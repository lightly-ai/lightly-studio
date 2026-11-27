import useAuth from '$lib/hooks/useAuth/useAuth';
import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';

/**
 * Whether the current user may create annotation classes.
 * Only editors and admins can; without a role (standalone mode) it is allowed.
 */
export function useCanCreateAnnotationClass(): boolean {
    return hasMinimumRole(useAuth().user?.role, 'editor');
}
