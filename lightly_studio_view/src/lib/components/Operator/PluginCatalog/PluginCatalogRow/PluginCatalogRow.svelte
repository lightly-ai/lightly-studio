<script lang="ts">
    import { Check, Download, LoaderCircle } from '@lucide/svelte';
    import { Button } from '$lib/components/ui/button';
    import {
        InstallJobStatus,
        type CatalogPluginView,
        type InstallJob
    } from '$lib/api/lightly_studio_local';

    interface Props {
        plugin: CatalogPluginView;
        /** The last install job of this plugin in this session. */
        job?: InstallJob;
        installAllowed: boolean;
        onInstall: (plugin: CatalogPluginView) => void;
    }

    let { plugin, job, installAllowed, onInstall }: Props = $props();

    const isInstalling = $derived(
        job?.status === InstallJobStatus.QUEUED || job?.status === InstallJobStatus.RUNNING
    );
    const isInstalled = $derived(plugin.installed || job?.status === InstallJobStatus.SUCCEEDED);
    const hasFailed = $derived(job?.status === InstallJobStatus.FAILED);
</script>

<li class="flex flex-col gap-2 p-3 text-sm">
    <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
            <p class="font-medium text-foreground">{plugin.name}</p>
            {#if plugin.description}
                <p class="mt-0.5 text-muted-foreground">{plugin.description}</p>
            {/if}
        </div>
        {#if isInstalled}
            <span class="inline-flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
                <Check class="size-3.5" /> Installed
            </span>
        {:else if isInstalling}
            <Button size="xs" variant="outline" disabled>
                <LoaderCircle class="animate-spin" /> Installing…
            </Button>
        {:else if installAllowed}
            <Button size="xs" variant="outline" onclick={() => onInstall(plugin)}>
                <Download />
                {hasFailed ? 'Retry' : 'Install'}
            </Button>
        {/if}
    </div>
    {#if isInstalling && job?.log}
        <p class="truncate font-mono text-xs text-muted-foreground">{job.log.split('\n').at(-1)}</p>
    {/if}
    {#if hasFailed}
        <details class="text-xs text-destructive-text">
            <summary class="cursor-pointer">{job?.error_message || 'The install failed.'}</summary>
            {#if job?.log}
                <pre
                    class="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-muted p-2 text-muted-foreground">{job.log}</pre>
            {/if}
        </details>
    {/if}
</li>
