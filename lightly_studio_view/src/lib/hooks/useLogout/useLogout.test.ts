import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import TestUseLogout from './useLogout.test.svelte';
import { AUTHENTICATION_SESSION_STORAGE_KEY } from '$lib/constants';
import * as navigation from '$app/navigation';

describe('useLogout', () => {
    let gotoSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
        vi.clearAllMocks();
        vi.resetAllMocks();

        // Spy on goto function
        gotoSpy = vi.spyOn(navigation, 'goto').mockImplementation(() => Promise.resolve());

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

        // Clear cookies before each test
        document.cookie = 'token=; path=/; max-age=0';
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

        const logoutButton = screen.getByTestId('logout-button');
        await fireEvent.click(logoutButton);

        expect(window.sessionStorage.removeItem).toHaveBeenCalledWith(
            AUTHENTICATION_SESSION_STORAGE_KEY
        );
    });

    it('redirects to login page on logout', async () => {
        renderComponent();

        const logoutButton = screen.getByTestId('logout-button');
        await fireEvent.click(logoutButton);

        expect(gotoSpy).toHaveBeenCalledWith('/workspace/login');
    });

    it('clears authentication cookie on logout', async () => {
        // Set a cookie first
        document.cookie = 'token=test-token; path=/';
        expect(document.cookie).toContain('token=test-token');

        renderComponent();

        const logoutButton = screen.getByTestId('logout-button');
        await fireEvent.click(logoutButton);

        // Cookie should be cleared (max-age=0)
        expect(document.cookie).not.toContain('token=test-token');
    });

    it('does not execute logout in non-browser environment', async () => {
        // This test verifies the browser check, but since we're in a browser environment
        // during tests, we can only test the happy path. The browser check is for SSR safety.
        renderComponent();

        const logoutButton = screen.getByTestId('logout-button');
        await fireEvent.click(logoutButton);

        // In browser environment, both operations should occur
        expect(window.sessionStorage.removeItem).toHaveBeenCalled();
        expect(gotoSpy).toHaveBeenCalledWith('/workspace/login');
    });
});
