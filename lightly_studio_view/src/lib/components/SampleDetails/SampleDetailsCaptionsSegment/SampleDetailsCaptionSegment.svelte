<script lang="ts">
    import type { CaptionView } from '$lib/api/lightly_studio_local';
    import Segment from '$lib/components/Segment/Segment.svelte';
    import CaptionField from '$lib/components/CaptionField/CaptionField.svelte';
    import CreateCaptionField from '$lib/components/CaptionField/CreateCaptionField.svelte';
    import CaptionSegmentRibbon from '$lib/components/CaptionSegmentRibbon/CaptionSegmentRibbon.svelte';
    import MatchScoreFilterChips from './MatchScoreFilterChips.svelte';
    import { useCreateCaption } from '$lib/hooks/useCreateCaption/useCreateCaption';
    import { useDeleteCaption } from '$lib/hooks/useDeleteCaption/useDeleteCaption';
    import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
    import { useCollectionWithChildren } from '$lib/hooks/useCollection/useCollection';
    import { addCaptionDeleteToUndoStack } from '$lib/services/addCaptionDeleteToUndoStack';
    import { page } from '$app/state';
    import { toast } from 'svelte-sonner';
    import {
        findActiveCaptionAtTime,
        getCaptionMatchScore,
        triageCaptions,
        type MatchScoreFilter
    } from '$lib/utils';

    interface SampleDetailsCaptionSegmentProps {
        captions: CaptionView[] | undefined;
        refetch: () => void;
        sampleId: string;
        /** Parent video id for segment frame ribbons (video details only). */
        videoId?: string;
        /** Current playback time used to highlight the active caption. */
        currentTimeS?: number;
        /** Caption id selected for segment-loop review. */
        selectedCaptionId?: string | null;
        /** Called when the user picks a caption row for review. */
        onSelectCaption?: (captionId: string) => void;
    }

    let {
        captions,
        refetch,
        sampleId,
        videoId,
        currentTimeS,
        selectedCaptionId = null,
        onSelectCaption
    }: SampleDetailsCaptionSegmentProps = $props();

    const { isEditingMode, addReversibleAction } = useGlobalStorage();

    const { deleteCaption } = useDeleteCaption();
    const { createCaption } = useCreateCaption();
    const datasetId = $derived(page.params.dataset_id!);
    const { refetch: refetchRootCollection } = $derived.by(() =>
        useCollectionWithChildren({ collectionId: datasetId })
    );

    let matchFilter = $state<MatchScoreFilter>('all');

    const captionList = $derived(captions ?? []);
    const hasMatchScores = $derived(
        captionList.some((caption) => getCaptionMatchScore(caption.metadata_dict) !== null)
    );
    const visibleCaptions = $derived(triageCaptions(captionList, matchFilter));
    const playheadCaptionId = $derived(
        currentTimeS === undefined
            ? null
            : (findActiveCaptionAtTime(captionList, currentTimeS)?.sample_id ?? null)
    );
    const activeCaptionId = $derived(playheadCaptionId ?? selectedCaptionId);
    const ribbonCaption = $derived(
        videoId
            ? (captionList.find((caption) => caption.sample_id === activeCaptionId) ?? null)
            : null
    );

    $effect(() => {
        if (!activeCaptionId) return;
        const row = document.querySelector(`[data-caption-id="${activeCaptionId}"]`);
        row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    });

    const handleDeleteCaption = async (captionId: string) => {
        const caption = captions?.find((c) => c.sample_id === captionId);
        if (!caption) return;

        try {
            addCaptionDeleteToUndoStack({
                text: caption.text ?? '',
                parentSampleId: sampleId,
                addReversibleAction,
                createCaption,
                refetch
            });
            await deleteCaption(captionId);
            toast.success('Caption deleted successfully');
            refetch();
        } catch (error) {
            toast.error('Failed to delete caption. Please try again.');
            console.error('Error deleting caption:', error);
        }
    };

    const onCreateCaption = async (sampleId: string, text: string): Promise<boolean> => {
        try {
            await createCaption({ parent_sample_id: sampleId, text });
            toast.success('Caption created successfully');
            refetch();

            if (!captions?.length) refetchRootCollection();
            return true;
        } catch (error) {
            toast.error('Failed to create caption. Please try again.');
            console.error('Error creating caption:', error);
            return false;
        }
    };
</script>

<Segment title="Captions">
    <div class="flex flex-col gap-3 space-y-4">
        {#if hasMatchScores}
            <MatchScoreFilterChips value={matchFilter} onChange={(filter) => (matchFilter = filter)} />
        {/if}

        {#if ribbonCaption?.temporal_span_details && videoId}
            <CaptionSegmentRibbon
                {videoId}
                startTimeS={ribbonCaption.temporal_span_details.start_time_s}
                endTimeS={ribbonCaption.temporal_span_details.end_time_s}
            />
        {/if}

        <div class="flex flex-col gap-2" data-testid="captions-list">
            {#each visibleCaptions as caption (caption.sample_id)}
                <CaptionField
                    {caption}
                    isActive={caption.sample_id === activeCaptionId}
                    onSelect={onSelectCaption
                        ? () => onSelectCaption(caption.sample_id)
                        : undefined}
                    onDeleteCaption={() => handleDeleteCaption(caption.sample_id)}
                    onUpdate={refetch}
                />
            {/each}
            {#if visibleCaptions.length === 0 && captionList.length > 0}
                <p class="text-sm text-muted-foreground" data-testid="captions-filter-empty">
                    No captions in this match band.
                </p>
            {/if}
            {#if $isEditingMode}
                <CreateCaptionField onCreate={(text) => onCreateCaption(sampleId, text)} />
            {/if}
        </div>
    </div>
</Segment>
