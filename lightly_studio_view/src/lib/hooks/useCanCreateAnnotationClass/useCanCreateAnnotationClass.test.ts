import { describe, expect, it, vi } from 'vitest';
import useAuth from '$lib/hooks/useAuth/useAuth';
import { useCanCreateAnnotationClass } from './useCanCreateAnnotationClass';

vi.mock('$lib/hooks/useAuth/useAuth');

describe('useCanCreateAnnotationClass', () => {
    it.each([
        [undefined, true],
        ['admin', true],
        ['editor', true],
        ['labeler', false],
        ['viewer', false]
    ] as const)('role %s -> %s', (role, expected) => {
        vi.mocked(useAuth).mockReturnValue({
            isAuthenticated: !!role,
            user: role ? { role, email: 'a@b.c' } : undefined
        } as ReturnType<typeof useAuth>);

        expect(useCanCreateAnnotationClass()).toBe(expected);
    });
});
