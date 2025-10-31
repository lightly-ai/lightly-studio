<script lang="ts">
    import { browser } from '$app/environment';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { useSettings } from '$lib/hooks/useSettings';
    import { usePostHog } from '$lib/hooks/usePostHog';
    import { useAuth } from '$lib/hooks/useAuth';
    import { i18n } from '$lib/i18n';
    import { ParaglideJS } from '@inlang/paraglide-sveltekit';
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import { onMount } from 'svelte';
    import '../app.css';
    import { Toaster } from 'svelte-sonner';
    import { client } from '$lib/api/lightly_studio_local/client.gen';

    interface ApiErrorWithStatus {
        error?: string;
        status?: number;
    }

    const auth = useAuth();
    const { isAuthenticated } = auth;

    // Route guard: protect routes by redirecting to login when not authenticated
    $effect(() => {
        if (browser) {
            const currentPath = page.url.pathname;
            const isLoginPage = currentPath === '/login';
            const authenticated = $isAuthenticated;

            // Only redirect to login if NOT on login page and NOT authenticated
            if (!isLoginPage && !authenticated) {
                goto('/login');
            }
        }
    });

    // Add request interceptor to inject Authorization header with JWT token
    client.interceptors.request.use((request) => {
        const token = auth.getToken();
        if (token) {
            request.headers.set('Authorization', `Bearer ${token}`);
        }
        return request;
    });

    // Add error interceptor to preserve HTTP status code on errors and handle 401
    client.interceptors.error.use((error: unknown, response: Response) => {
        if (response && typeof error === 'object' && error !== null) {
            (error as ApiErrorWithStatus).status = response.status;
        }

        // Handle 401 Unauthorized - clear auth and redirect to login
        if (response && response.status === 401) {
            if (browser) {
                auth.logout();
            }
        }

        return error;
    });

    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                enabled: browser,
                // Don't retry client errors (4xx).
                // Only retry network errors and 5xx server errors up to 3 times.
                retry: (failureCount, error: unknown) => {
                    const status = (error as ApiErrorWithStatus)?.status;
                    if (status && status >= 400 && status < 500) {
                        return false;
                    }
                    return failureCount < 3;
                }
            }
        }
    });

    // Initialize settings and analytics once at startup
    onMount(() => {
        if (browser) {
            useSettings().initSettings();
            usePostHog().init();
        }
    });

    let { children } = $props();
</script>

<ParaglideJS {i18n}>
    <QueryClientProvider client={queryClient}>
        <div class="flex h-full w-full flex-col">
            {@render children()}
            <Toaster richColors />
        </div>
    </QueryClientProvider>
</ParaglideJS>
