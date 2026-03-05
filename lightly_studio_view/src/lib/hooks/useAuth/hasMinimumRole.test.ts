import { describe, it, expect } from 'vitest';
import { hasMinimumRole } from './hasMinimumRole';
import type { Role } from './getLightlyEnterpriseSession/getLightlyEnterpriseSession';

describe('hasMinimumRole', () => {
    it('returns true when userRole is undefined (standalone OSS mode)', () => {
        expect(hasMinimumRole(undefined, 'admin')).toBe(true);
        expect(hasMinimumRole(undefined, 'editor')).toBe(true);
        expect(hasMinimumRole(undefined, 'labeler')).toBe(true);
        expect(hasMinimumRole(undefined, 'viewer')).toBe(true);
    });

    describe('viewer role', () => {
        const role: Role = 'viewer';

        it('has viewer permission', () => {
            expect(hasMinimumRole(role, 'viewer')).toBe(true);
        });

        it('does not have labeler permission', () => {
            expect(hasMinimumRole(role, 'labeler')).toBe(false);
        });

        it('does not have editor permission', () => {
            expect(hasMinimumRole(role, 'editor')).toBe(false);
        });

        it('does not have admin permission', () => {
            expect(hasMinimumRole(role, 'admin')).toBe(false);
        });
    });

    describe('labeler role', () => {
        const role: Role = 'labeler';

        it('has viewer permission', () => {
            expect(hasMinimumRole(role, 'viewer')).toBe(true);
        });

        it('has labeler permission', () => {
            expect(hasMinimumRole(role, 'labeler')).toBe(true);
        });

        it('does not have editor permission', () => {
            expect(hasMinimumRole(role, 'editor')).toBe(false);
        });

        it('does not have admin permission', () => {
            expect(hasMinimumRole(role, 'admin')).toBe(false);
        });
    });

    describe('editor role', () => {
        const role: Role = 'editor';

        it('has viewer permission', () => {
            expect(hasMinimumRole(role, 'viewer')).toBe(true);
        });

        it('has labeler permission', () => {
            expect(hasMinimumRole(role, 'labeler')).toBe(true);
        });

        it('has editor permission', () => {
            expect(hasMinimumRole(role, 'editor')).toBe(true);
        });

        it('does not have admin permission', () => {
            expect(hasMinimumRole(role, 'admin')).toBe(false);
        });
    });

    describe('admin role', () => {
        const role: Role = 'admin';

        it('has viewer permission', () => {
            expect(hasMinimumRole(role, 'viewer')).toBe(true);
        });

        it('has labeler permission', () => {
            expect(hasMinimumRole(role, 'labeler')).toBe(true);
        });

        it('has editor permission', () => {
            expect(hasMinimumRole(role, 'editor')).toBe(true);
        });

        it('has admin permission', () => {
            expect(hasMinimumRole(role, 'admin')).toBe(true);
        });
    });

    it('returns false for an unknown role', () => {
        const unknownRole = 'moderator' as Role;
        expect(hasMinimumRole(unknownRole, 'viewer')).toBe(false);
        expect(hasMinimumRole(unknownRole, 'admin')).toBe(false);
    });
});
