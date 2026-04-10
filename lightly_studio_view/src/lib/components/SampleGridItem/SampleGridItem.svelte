<script lang="ts">
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import type { Snippet } from 'svelte';
    import SelectableBox from '../SelectableBox/SelectableBox.svelte';
    import useAuth from '$lib/hooks/useAuth/useAuth';
    import { hasMinimumRole } from '$lib/hooks/useAuth/hasMinimumRole';

    type SampleGridItemProps = {
        style?: string;
        dataTestId: string;
        sampleId: string;
        dataSampleName: string;
        index: number;
        collectionId: string;
        ondblclick?: (event: MouseEvent) => void;
        onSelect?: (event: { sampleId: string; index: number; shiftKey: boolean }) => void;
        item: Snippet;
    };

    const {
        style,
        dataTestId,
        sampleId,
        dataSampleName,
        index,
        ondblclick,
        onSelect,
        collectionId,
        item
    }: SampleGridItemProps = $props();

    const { user } = useAuth();
    const { getSelectedSampleIds, toggleSampleSelection } = useGlobalStorage();

    const selectedSampleIds = getSelectedSampleIds(collectionId);

    function handleOnClick(event: MouseEvent) {
        event.preventDefault();
        if (onSelect) {
            onSelect({ sampleId, index, shiftKey: event.shiftKey });
            return;
        }
        toggleSampleSelection(sampleId, collectionId);
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            if (onSelect) {
                onSelect({ sampleId, index, shiftKey: event.shiftKey });
                return;
            }
            toggleSampleSelection(sampleId, collectionId);
        }
    }
</script>

<div class="select-none" {style}>
    <div
        class="relative overflow-hidden rounded-lg"
        class:grid-item-selected={$selectedSampleIds.has(sampleId)}
        style="width: var(--sample-width); height: var(--sample-height);"
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
        {#if hasMinimumRole(user?.role, 'labeler') && $selectedSampleIds.has(sampleId)}
            <div class="pointer-events-none absolute right-2 top-1.5 z-10">
                <SelectableBox onSelect={() => undefined} isSelected={true} />
            </div>
        {/if}
        {@render item()}
    </div>
</div>
