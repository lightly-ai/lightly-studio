<script lang="ts">
    import { writable } from 'svelte/store';
    import { Button } from '$lib/components/ui/button';
    import { useGlobalStorage, useImageFilters } from '$lib/hooks';
    import type { ExportType } from '../exportOptions';
    import { buildExportCode } from './buildExportCode';

    interface Props {
        /** The collection whose samples are exported. */
        collectionId: string;
        /** Name of the dataset, as passed to `ls.ImageDataset.load()`. */
        datasetName: string;
        /** The export format selected in the dialog. */
        exportType: ExportType;
        /** Whether the images are bundled with the COCO object detections. */
        includeImages: boolean;
        /** Annotation sources of the collection. */
        annotationSources: { id: string; name: string }[];
        /** The annotation source selected in the dialog. */
        selectedAnnotationSourceId: string | undefined;
    }

    let {
        collectionId,
        datasetName,
        exportType,
        includeImages,
        annotationSources,
        selectedAnnotationSourceId
    }: Props = $props();

    const { tags } = useGlobalStorage();
    const { imageFilter } = useImageFilters();
    const isOpen = writable(false);
    const isCopied = writable(false);

    const result = $derived(
        buildExportCode({
            datasetName,
            imageFilter: $imageFilter,
            tags: $tags[collectionId] ?? [],
            exportType,
            includeImages,
            annotationSources,
            selectedAnnotationSourceId
        })
    );

    const copyCode = async () => {
        if (!result.code) return;
        await navigator.clipboard.writeText(result.code);
        isCopied.set(true);
    };
</script>

<div class="flex flex-col gap-2 pb-2 text-sm" data-testid="export-as-code">
    <Button variant="outline" size="sm" onclick={() => isOpen.update((open) => !open)}>
        {$isOpen ? 'Hide code' : 'Copy as code'}
    </Button>
    {#if $isOpen && result.code}
        <p class="text-muted-foreground">Run the same export with the LightlyStudio Python SDK:</p>
        <pre class="max-h-48 overflow-auto rounded bg-muted p-2 text-xs"><code>{result.code}</code
            ></pre>
        <Button variant="outline" size="sm" onclick={copyCode}>
            {$isCopied ? 'Copied' : 'Copy code'}
        </Button>
    {:else if $isOpen}
        <p class="text-muted-foreground">{result.reason}</p>
    {/if}
</div>
