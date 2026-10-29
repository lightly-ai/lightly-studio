<script lang="ts">
    import { writable } from 'svelte/store';
    import { Button } from '$lib/components/ui/button';
    import { useGlobalStorage, useImageFilters } from '$lib/hooks';
    import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
    import type { ExportType } from '../exportOptions';
    import { buildExportCode } from './buildExportCode';
    import { highlightPython, type PythonTokenKind } from './highlightPython';

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
    // The filter panel has loaded the bounds of the open collection already.
    const { dimensionsBounds } = useDimensions();
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
            selectedAnnotationSourceId,
            dimensionBounds: $dimensionsBounds
        })
    );

    const tokens = $derived(result.code ? highlightPython(result.code) : []);
    const TOKEN_CLASSES: Record<PythonTokenKind, string> = {
        keyword: 'text-purple-400',
        string: 'text-emerald-400',
        comment: 'italic text-muted-foreground',
        number: 'text-amber-300',
        plain: 'text-foreground'
    };

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
        <!-- No height cap here: the dialog body scrolls, so the code does not scroll twice. -->
        <div class="relative rounded border border-border bg-muted">
            <Button
                variant="outline"
                size="sm"
                class="absolute right-2 top-2 h-7 px-2 text-xs"
                onclick={copyCode}
            >
                {$isCopied ? 'Copied' : 'Copy code'}
            </Button>
            <pre class="overflow-x-auto p-3 pr-24 font-mono text-xs leading-5"><code
                    >{#each tokens as token, index (index)}<span
                            class={TOKEN_CLASSES[token.kind]}
                            data-token={token.kind}>{token.text}</span
                        >{/each}</code
                ></pre>
        </div>
    {:else if $isOpen}
        <p class="text-muted-foreground">{result.reason}</p>
    {/if}
</div>
