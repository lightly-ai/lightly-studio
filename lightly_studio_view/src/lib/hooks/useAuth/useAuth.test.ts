import { vi } from 'vitest';
import useAuth from './useAuth';
import * as getLightlyEnterpriseSessionModule from './getLightlyEnterpriseSession/getLightlyEnterpriseSession';

vi.mock('./getLightlyEnterpriseSession/getLightlyEnterpriseSession', () => ({
    getLightlyEnterpriseSession: vi.fn()
}));

describe('useAuth', () => {
    const mockGetLightlyEnterpriseSession = vi.mocked(
        getLightlyEnterpriseSessionModule.getLightlyEnterpriseSession
    );

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('returns unauthenticated state when session is null', () => {
        mockGetLightlyEnterpriseSession.mockReturnValue(null);

        const result = useAuth();

        expect(result.token).toBeUndefined();
        expect(result.user).toBeUndefined();
        expect(result.isAuthenticated).toBe(false);
    });

    it('returns authenticated state when session exists', () => {
        const mockSession = {
            token: 'test-token-123',
            user: {
                role: 'admin' as const,
                email: 'admin@example.com'
            },
            settings: {
                showDashboard: true
            }
        };
        mockGetLightlyEnterpriseSession.mockReturnValue(mockSession);

        const result = useAuth();

        expect(result.token).toBe('test-token-123');
        expect(result.user).toEqual(mockSession.user);
        expect(result.isAuthenticated).toBe(true);
    });
});
