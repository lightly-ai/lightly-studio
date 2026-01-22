import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ErrorPage from './+error.svelte';
import '@testing-library/jest-dom';
import * as appStores from '$app/stores';
import * as clientModule from '$lib/api/lightly_studio_local/client.gen';
import { readable } from 'svelte/store';

vi.mock('$app/stores');
vi.mock('$lib/api/lightly_studio_local/client.gen');

describe('+error.svelte', () => {
    const mockReload = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        Object.defineProperty(window, 'location', {
            value: { reload: mockReload },
            writable: true
        });

        vi.mocked(clientModule.client).getConfig = vi.fn().mockReturnValue({
            baseUrl: 'http://localhost:8001/'
        });
    });

    describe('API Connection Error', () => {
        it('should display API error message when error message includes "fetch"', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'fetch failed' },
                    status: 503
                })
            );

            render(ErrorPage);

            expect(screen.getByText('Unable to Connect to API')).toBeInTheDocument();
            expect(
                screen.getByText('The Lightly Studio API server is not running or is unreachable.')
            ).toBeInTheDocument();
        });

        it('should display API error message when error message includes "connection"', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'connection refused' },
                    status: 500
                })
            );

            render(ErrorPage);

            expect(screen.getByText('Unable to Connect to API')).toBeInTheDocument();
        });

        it('should display API error message when error message includes "ECONNREFUSED"', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'ECONNREFUSED' },
                    status: 500
                })
            );

            render(ErrorPage);

            expect(screen.getByText('Unable to Connect to API')).toBeInTheDocument();
        });

        it('should display API error message when status is 500', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'Internal server error' },
                    status: 500
                })
            );

            render(ErrorPage);

            expect(screen.getByText('Unable to Connect to API')).toBeInTheDocument();
        });

        it('should display API error message when status is 503', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'Service unavailable' },
                    status: 503
                })
            );

            render(ErrorPage);

            expect(screen.getByText('Unable to Connect to API')).toBeInTheDocument();
        });

        it('should display the API URL from client config', () => {
            vi.mocked(clientModule.client).getConfig = vi.fn().mockReturnValue({
                baseUrl: 'http://example.com:9000/'
            });

            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'fetch failed' },
                    status: 503
                })
            );

            render(ErrorPage);

            const codeElements = screen.getAllByText('http://example.com:9000/');
            expect(codeElements.length).toBeGreaterThan(0);
        });

        it('should display default API URL when client config returns empty', () => {
            vi.mocked(clientModule.client).getConfig = vi.fn().mockReturnValue({
                baseUrl: ''
            });

            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'fetch failed' },
                    status: 503
                })
            );

            render(ErrorPage);

            const codeElements = screen.getAllByText('http://localhost:8001/');
            expect(codeElements.length).toBeGreaterThan(0);
        });

        it('should display instructions to start the API server', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'fetch failed' },
                    status: 503
                })
            );

            render(ErrorPage);

            expect(screen.getByText('To get started:')).toBeInTheDocument();
            expect(
                screen.getByText(/Make sure the Lightly Studio API server is running at/)
            ).toBeInTheDocument();
            expect(
                screen.getByText('Check that the API is accessible at the configured URL')
            ).toBeInTheDocument();
            expect(
                screen.getByText('Refresh this page once the API is running')
            ).toBeInTheDocument();
        });
    });

    describe('Generic Error', () => {
        it('should display generic error message for non-API errors', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'Page not found' },
                    status: 404
                })
            );

            render(ErrorPage);

            expect(screen.getByText('Error 404')).toBeInTheDocument();
            expect(screen.getByText('Page not found')).toBeInTheDocument();
        });

        it('should display error status in title', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'Bad request' },
                    status: 400
                })
            );

            render(ErrorPage);

            expect(screen.getByText('Error 400')).toBeInTheDocument();
        });

        it('should display default error message when error message is undefined', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: null,
                    status: 400
                })
            );

            render(ErrorPage);

            expect(screen.getByText('An unexpected error occurred')).toBeInTheDocument();
        });

        it('should not display API-specific instructions for generic errors', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'Not found' },
                    status: 404
                })
            );

            render(ErrorPage);

            expect(screen.queryByText('To get started:')).not.toBeInTheDocument();
            expect(screen.queryByText('Expected API URL:')).not.toBeInTheDocument();
        });
    });

    describe('Refresh Button', () => {
        it('should render refresh button', () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'Error' },
                    status: 500
                })
            );

            render(ErrorPage);

            expect(screen.getByRole('button', { name: 'Refresh Page' })).toBeInTheDocument();
        });

        it('should reload the page when refresh button is clicked', async () => {
            vi.spyOn(appStores, 'page', 'get').mockReturnValue(
                readable({
                    error: { message: 'Error' },
                    status: 500
                })
            );

            render(ErrorPage);
            const button = screen.getByRole('button', { name: 'Refresh Page' });

            await button.click();

            expect(mockReload).toHaveBeenCalled();
        });
    });
});
