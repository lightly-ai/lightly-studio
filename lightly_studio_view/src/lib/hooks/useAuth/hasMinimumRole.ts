import type { Role } from './getLightlyEnterpriseSession/getLightlyEnterpriseSession';

const ROLE_HIERARCHY: Record<Role, ReadonlySet<Role>> = {
    viewer: new Set(['viewer']),
    labeler: new Set(['viewer', 'labeler']),
    editor: new Set(['viewer', 'labeler', 'editor']),
    admin: new Set(['viewer', 'labeler', 'editor', 'admin'])
};

/**
 * Checks if a user's role meets the minimum required role.
 * Returns true when no role is provided (standalone OSS mode).
 */
export function hasMinimumRole(userRole: Role | undefined, minimum: Role): boolean {
    if (!userRole) return true;
    return ROLE_HIERARCHY[userRole]?.has(minimum) ?? false;
}
