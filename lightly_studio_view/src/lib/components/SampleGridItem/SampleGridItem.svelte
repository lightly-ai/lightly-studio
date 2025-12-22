<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { Snippet } from 'svelte';
    import SelectableBox from '../SelectableBox/SelectableBox.svelte';

    type SampleGridItemProps = {
        style?: string;
        dataTestId: string;
        sampleId: string;
        dataSampleName: string;
        index: number;
        collectionId: string;
        ondblclick?: (event: MouseEvent) => void;
        item: Snippet;
    };

    const {
        style,
        dataTestId,
        sampleId,
        dataSampleName,
        index,
        ondblclick,
        collectionId,
        item
    }: SampleGridItemProps = $props();

    const { getSelectedSampleIds, toggleSampleSelection } = useGlobalStorage();

    const selectedSampleIds = getSelectedSampleIds(collectionId);

    function handleOnClick(event: MouseEvent) {
        event.preventDefault();
        toggleSampleSelection(sampleId, collectionId);
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleSampleSelection(sampleId, collectionId);
        }
    }
</script>

<div
    class="relative"
    class:sample-selected={$selectedSampleIds.has(sampleId)}
    {style}
    data-testid={dataTestId}
    data-sample-id={sampleId}
    data-sample-name={dataSampleName}
    data-index={index}
    {ondblclick}
    onclick={handleOnClick}
    onkeydown={handleKeyDown}
    aria-label={`View sample: ${dataSampleName}`}
    role="button"
    tabindex="0"
>
    <div class="absolute right-7 top-1 z-10">
        <SelectableBox onSelect={() => undefined} isSelected={$selectedSampleIds.has(sampleId)} />
    </div>

    <div
        class="relative overflow-hidden rounded-lg"
        style="width: var(--sample-width); height: var(--sample-height);"
    >
        {@render item()}
    </div>
</div>

<style>
    .sample-selected {
        outline: drop-shadow(1px 1px 1px hsl(var(--primary)))
            drop-shadow(1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px -1px 1px hsl(var(--primary)))
            drop-shadow(-1px 1px 1px hsl(var(--primary)));
    }
</style>
