<script lang="ts">
    import { PointCloudViewer } from '$lib/components/PointCloudViewer';
    import { useCloudPointFrame } from '$lib/hooks';

    interface Props {
        datasetId?: string;
        recordingId?: string;
        channelId?: number;
        timestampNs?: string;
    }

    let { datasetId = '', recordingId = '', channelId = 0, timestampNs = '' }: Props = $props();
    const { query } = useCloudPointFrame(() => ({
        datasetId,
        recordingId,
        channels: timestampNs ? [{ channelId, timestampNs }] : []
    }));
</script>

<div class="flex h-full min-h-[420px] flex-col bg-background text-foreground">
    <div class="flex items-center gap-4 border-b px-4 py-2 text-sm">
        {#if query.isPending}
            <span>Enter recording details to load a cloud.</span>
        {:else if query.isError}
            <span class="text-destructive">{query.error.message}</span>
        {:else if query.data}
            <span>{query.data.batch.count.toLocaleString()} points</span>
            <span
                >Channels {query.data.channels.map((channel) => channel.channelId).join(', ')}</span
            >
            <span>Frame {query.data.frameId || 'unknown'}</span>
        {/if}
    </div>
    {#if query.data}
        <div class="min-h-0 flex-1">
            <PointCloudViewer
                batch={query.data.batch}
                colorMode={query.data.batch.colors ? 'rgb' : 'intensity'}
            />
        </div>
    {/if}
</div>
