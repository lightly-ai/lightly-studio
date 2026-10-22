<script lang="ts">
    import { AlertCircle, LoaderCircle } from '@lucide/svelte';
    import { usePluginCatalog, usePluginInstall } from '$lib/hooks';
    import PluginCatalogRow from './PluginCatalogRow/PluginCatalogRow.svelte';

    interface Props {
        /** Fetch the catalog only while it is visible. */
        isVisible: boolean;
    }

    let { isVisible }: Props = $props();

    const { query } = usePluginCatalog(() => ({ enabled: isVisible }));
    const { jobs, install } = usePluginInstall();

    const errorMessage = $derived(
        (query.error as { error?: string } | null)?.error ?? 'The plugin catalog is unavailable.'
    );
</script>

{#if query.isPending}
    <div class="flex items-center gap-2 p-4 text-sm text-muted-foreground">
        <LoaderCircle class="size-4 animate-spin" />
        <span>Loading the plugin catalog…</span>
    </div>
{:else if query.isError}
    <div class="flex items-start gap-2 p-4 text-sm text-destructive-text">
        <AlertCircle class="mt-0.5 size-4 shrink-0" />
        <span>{errorMessage} Check the network connection, then open this tab again.</span>
    </div>
{:else}
    {#if !query.data.install_allowed}
        <p class="border-b px-3 py-2 text-xs text-muted-foreground">
            Installs from the GUI are only available on the machine that runs LightlyStudio.
        </p>
    {/if}
    <ul class="divide-y divide-border">
        {#each query.data.plugins as plugin (plugin.id)}
            <PluginCatalogRow
                {plugin}
                job={$jobs[plugin.id]}
                installAllowed={query.data.install_allowed}
                onInstall={install}
            />
        {/each}
    </ul>
{/if}
