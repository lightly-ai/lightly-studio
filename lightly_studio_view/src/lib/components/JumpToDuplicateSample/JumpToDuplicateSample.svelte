<script lang="ts">
    import { page } from '$app/state';
    import { routeHelpers } from '$lib/routes';
    import Button from '$lib/components/ui/button/button.svelte';
    import { getDuplicateOfSampleId } from './getDuplicateOfSampleId';

    interface JumpToDuplicateSampleProps {
        metadataDict: unknown;
        datasetId: string;
    }

    const { metadataDict, datasetId }: JumpToDuplicateSampleProps = $props();

    const duplicateOfSampleId = $derived(getDuplicateOfSampleId(metadataDict));
    const collectionType = $derived(page.params.collection_type!);
    const collectionId = $derived(page.params.collection_id!);

    const href = $derived(
        duplicateOfSampleId
            ? routeHelpers.toVideosDetails({
                  datasetId,
                  collectionType,
                  collectionId,
                  sampleId: duplicateOfSampleId
              })
            : null
    );
</script>

{#if href}
    <Button
        variant="secondary"
        class="mt-4 w-full"
        data-testid="jump-to-duplicate-sample-button"
        {href}
    >
        Jump to kept sample
    </Button>
{/if}
