<script lang="ts">
    import { Button } from '$lib/components/ui/button';
    import { useMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
    import { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
    import { MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY } from '$lib/constants';
    import { MATCH_SCORE_LOW_MAX } from '$lib/utils';

    const { metadataInfo } = useMetadataFilters();
    const { filterParams, setLowCaptionMatch } = useVideoFilters();

    const hasMinMatchScore = $derived(
        ($metadataInfo ?? []).some((info) => info.name === MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY)
    );
    const isActive = $derived(!!$filterParams?.filters?.low_caption_match);
</script>

{#if hasMinMatchScore}
    <Button
        type="button"
        size="sm"
        variant={isActive ? 'default' : 'outline'}
        class="h-7 px-2.5 text-xs"
        onclick={() => setLowCaptionMatch(!isActive)}
        aria-pressed={isActive}
        data-testid="low-caption-match-filter"
        title={`Show videos whose worst caption match score is below ${MATCH_SCORE_LOW_MAX}`}
    >
        Low caption match
    </Button>
{/if}
