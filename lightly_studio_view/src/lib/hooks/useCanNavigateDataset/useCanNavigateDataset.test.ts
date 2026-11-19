import { describe, expect, it, vi } from 'vitest';
import useAuth from '$lib/hooks/useAuth/useAuth';
import { useCanNavigateDataset } from './useCanNavigateDataset';

vi.mock('$lib/hooks/useAuth/useAuth');

describe('useCanNavigateDataset', () => {
    it.each([
        [undefined, true],
        ['admin', true],
        ['editor', true],
        ['viewer', true],
        ['labeler', false]
    ] as const)('role %s -> %s', (role, expected) => {
        vi.mocked(useAuth).mockReturnValue({
            isAuthenticated: !!role,
            user: role ? { role, email: 'a@b.c' } : undefined
        } as ReturnType<typeof useAuth>);

        expect(useCanNavigateDataset()).toBe(expected);
    });
});
