<script lang="ts">
    import Segment from '$lib/components/Segment/Segment.svelte';
    import { formatInteger } from '$lib/utils';
    import type { ImageView } from '$lib/api/lightly_studio_local';
    import MetadataSegment from '../MetadataSegment/MetadataSegment.svelte';

    const {
        sample,
        showCustomMetadata = true
    }: {
        sample: ImageView;
        showCustomMetadata?: boolean;
    } = $props();

    const sample_details = $derived([
        { id: 'height', label: 'Height:', value: formatInteger(sample.height) + 'px' },
        { id: 'width', label: 'Width:', value: formatInteger(sample.width) + 'px' },
        { id: 'filename', label: 'Filename:', value: sample.file_name },
        { id: 'filepath', label: 'Filepath:', value: sample.file_path_abs }
    ]);
</script>

<Segment title="Sample details">
    <div class="grid grid-cols-[6rem_1fr] gap-y-3 text-diffuse-foreground">
        {#each sample_details as { label, value, id } (label)}
            <span class="text-sm">{label}</span>
            <span class="break-all text-sm" data-testid={`sample-metadata-${id}`}>{value}</span>
        {/each}
    </div>
</Segment>

{#if showCustomMetadata}
    <MetadataSegment metadata_dict={sample.metadata_dict} />
{/if}
