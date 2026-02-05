<script lang="ts">
    import { browser } from '$app/environment';
    import { useSettings } from '$lib/hooks/useSettings';
    import { usePostHog } from '$lib/hooks/usePostHog';
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import { onMount } from 'svelte';
    import '../app.css';
    import { Toaster } from 'svelte-sonner';
    import { client } from '$lib/api/lightly_studio_local/client.gen';

    interface ApiErrorWithStatus {
        error?: string;
        status?: number;
    }

    // Add error interceptor to preserve HTTP status code on errors.
    client.interceptors.error.use((error: unknown, response: Response) => {
        if (response && typeof error === 'object' && error !== null) {
            (error as ApiErrorWithStatus).status = response.status;
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
                },
                // Prevent circular reload issues:
                // - refetchOnWindowFocus: Disable automatic refetch when switching between DevTools/tabs
                // - refetchOnReconnect: Disable automatic refetch when network reconnects
                // - staleTime: Keep data fresh for 5 minutes before marking as stale (default is 0)
                // Without these settings, library updates or network changes can trigger cascading refetches
                refetchOnWindowFocus: false,
                refetchOnReconnect: false,
                staleTime: 1000 * 60 * 5 // 5 minutes
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

<QueryClientProvider client={queryClient}>
    <div class="flex h-full w-full flex-col">
        {@render children()}
        <Toaster richColors />
    </div>
</QueryClientProvider>
