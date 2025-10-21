<script lang="ts">
    import { Button } from '$lib/components/ui';
    import { Tooltip } from '$lib/components/ui/tooltip';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
    import { useRefineClassifiersPanel } from '$lib/hooks/useClassifiers/useRefineClassifiersPanel';
    import { useClassifiers } from '$lib/hooks/useClassifiers/useClassifiers';
    import NetworkIcon from '@lucide/svelte/icons/network';

    const { isCreateClassifiersPanelOpen } = useCreateClassifiersPanel();
    const { isRefineClassifiersPanelOpen } = useRefineClassifiersPanel();

    const { startCreateClassifier } = useClassifiers();
    const { selectedSampleIds } = useGlobalStorage();
</script>

<Tooltip content="">
    <Button
        variant={$selectedSampleIds.size > 0 ? 'default' : 'ghost'}
        class="flex items-center space-x-2"
        onclick={startCreateClassifier}
        disabled={$isCreateClassifiersPanelOpen ||
            $selectedSampleIds.size === 0 ||
            $isRefineClassifiersPanelOpen}
    >
        <NetworkIcon class="size-4" />
        <span>New Classifier</span>
    </Button>
</Tooltip>
