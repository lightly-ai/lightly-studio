<script lang="ts">
    import { page } from '$app/stores';
    import { client } from '$lib/api/lightly_studio_local/client.gen';
    import { Button } from '$lib/components/ui/button';
    import { derived } from 'svelte/store';

    const error = derived(page, ($page) => $page.error);
    const status = derived(page, ($page) => $page.status);

    // Get the API URL from the client config
    const apiUrl = derived(page, () => client.getConfig().baseUrl || 'http://localhost:8001/');

    // Check if error is related to API connection
    const isApiError = derived([error, status], ([$error, $status]) => {
        return (
            $error?.message?.includes('fetch') ||
            $error?.message?.includes('connection') ||
            $error?.message?.includes('ECONNREFUSED') ||
            $status === 500 ||
            $status === 503
        );
    });
</script>

<div class="flex min-h-screen items-center justify-center bg-background p-8">
    <div class="max-w-2xl rounded-xl border border-border bg-card p-12 text-center shadow-lg">
        {#if $isApiError}
            <div class="mb-6 text-6xl">⚠️</div>
            <h1 class="mb-4 text-3xl font-bold text-foreground">Unable to Connect to API</h1>
            <p class="mb-6 text-lg text-muted-foreground">
                The Lightly Studio API server is not running or is unreachable.
            </p>
            <div class="mb-6 rounded border-l-4 border-primary bg-muted p-4">
                <strong class="mb-2 block text-sm text-foreground">Expected API URL:</strong>
                <code
                    class="inline-block rounded bg-background px-2 py-1 font-mono text-sm font-semibold text-primary"
                >
                    {$apiUrl}
                </code>
            </div>
            <div class="mb-8 rounded-lg bg-muted p-6 text-left">
                <h2 class="mb-4 text-xl font-semibold text-foreground">To get started:</h2>
                <ol class="list-decimal space-y-2 pl-6 text-foreground">
                    <li>
                        Make sure the Lightly Studio API server is running at <code
                            class="rounded bg-muted px-1 py-0.5 font-mono text-sm text-muted-foreground"
                            >{$apiUrl}</code
                        >
                    </li>
                    <li>Check that the API is accessible at the configured URL</li>
                    <li>Refresh this page once the API is running</li>
                </ol>
            </div>
        {:else}
            <div class="mb-6 text-6xl">❌</div>
            <h1 class="mb-4 text-3xl font-bold text-foreground">Error {$status || ''}</h1>
            <p class="mb-8 text-lg text-muted-foreground">
                {$error?.message || 'An unexpected error occurred'}
            </p>
        {/if}

        <Button onclick={() => window.location.reload()} class="px-8 py-6 text-base">
            Refresh Page
        </Button>
    </div>
</div>
