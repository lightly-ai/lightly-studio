<script lang="ts">
    import { browser } from '$app/environment';
    import { useSettings } from '$lib/hooks/useSettings';
    import { usePostHog } from '$lib/hooks';
    import { QueryClient, QueryClientProvider } from '@tanstack/svelte-query';
    import { onMount } from 'svelte';
    import '../app.css';
    import { Toaster } from 'svelte-sonner';
    import { PluginExecutingOverlay } from '$lib/components/PluginExecutingOverlay';
    import { shouldRetryQuery } from '$lib/api/shouldRetryQuery';

    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                enabled: browser,
                retry: shouldRetryQuery
            }
        }
    });

    // Initialize settings and analytics once at startup
    onMount(() => {
        if (browser) {
            useSettings().initSettings();
            usePostHog();
        }
    });

    let { children } = $props();
    const { settingsStore } = useSettings();
</script>

<QueryClientProvider client={queryClient}>
    <div
        class="flex h-full w-full flex-col"
        class:nearest-neighbor={$settingsStore.image_interpolation === false}
    >
        {@render children()}
        <Toaster richColors />
        <PluginExecutingOverlay />
    </div>
</QueryClientProvider>

<style>
    .nearest-neighbor {
        image-rendering: pixelated;
        image-rendering: crisp-edges;
    }

    .nearest-neighbor :global(canvas) {
        image-rendering: auto;
    }
</style>
