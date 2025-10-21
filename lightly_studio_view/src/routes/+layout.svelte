<script lang="ts">
    import { browser } from '$app/environment';
    import { useSettings } from '$lib/hooks/useSettings';
    import { usePostHog } from '$lib/hooks/usePostHog';
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
