import { vi } from 'vitest';
import { getLightlyEnterpriseSession } from './getLightlyEnterpriseSession';

describe('getLightlyEnterpriseSession', () => {
    it('returns null when no session data exists', () => {
        const session = getLightlyEnterpriseSession();
        expect(session).toBeNull();
    });

    it('returns parsed session data when it exists', () => {
        const mockSession = {
            token: 'test-token',
            user: {
                role: 'admin',
                email: 'john.doe@gmail.com'
            },
            settings: {
                showDashboard: true
            }
        };
        sessionStorage.setItem('lightlyEnterprise', JSON.stringify(mockSession));

        const session = getLightlyEnterpriseSession();
        expect(session).toEqual(mockSession);
    });

    it('returns null when session data is invalid JSON', () => {
        const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        sessionStorage.setItem('lightlyEnterprise', 'invalid-json');

        const session = getLightlyEnterpriseSession();
        expect(session).toBeNull();
        expect(consoleErrorSpy).toHaveBeenCalled();

        consoleErrorSpy.mockRestore();
    });
});
