import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import TestUseLogout from './useLogout.test.svelte';
import { AUTHENTICATION_SESSION_STORAGE_KEY } from '$lib/constants';
import * as navigation from '$lib/utils/navigation';

const LOGOUT_ENDPOINT = '/auth/api/v1/logout';

describe('useLogout', () => {
    let redirectSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
        vi.clearAllMocks();
        vi.resetAllMocks();

        // Spy on the navigation helper so the test never touches window.location.
        redirectSpy = vi.spyOn(navigation, 'redirectTo').mockImplementation(() => {});

        // Mock sessionStorage
        Object.defineProperty(window, 'sessionStorage', {
            value: {
                getItem: vi.fn(),
                setItem: vi.fn(),
                removeItem: vi.fn(),
                clear: vi.fn()
            },
            writable: true
        });
    });

    const renderComponent = () => {
        return render(TestUseLogout);
    };

    it('should render without error', () => {
        renderComponent();
        expect(screen.getByTestId('logout-hook-test')).toBeDefined();
    });

    it('removes authentication token from sessionStorage on logout', async () => {
        renderComponent();

        await fireEvent.click(screen.getByTestId('logout-button'));

        expect(window.sessionStorage.removeItem).toHaveBeenCalledWith(
            AUTHENTICATION_SESSION_STORAGE_KEY
        );
    });

    it('navigates to the backend logout endpoint on logout', async () => {
        renderComponent();

        await fireEvent.click(screen.getByTestId('logout-button'));

        expect(redirectSpy).toHaveBeenCalledWith(LOGOUT_ENDPOINT);
    });
});
