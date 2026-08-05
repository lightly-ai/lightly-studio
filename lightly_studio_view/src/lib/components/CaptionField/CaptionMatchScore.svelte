<script lang="ts">
    import type { CaptionView } from '$lib/api/lightly_studio_local';
    import { Badge } from '$lib/components/ui/badge/index.js';
    import { CAPTION_SEGMENT_MATCH_SCORE_KEY } from '$lib/constants';

    const {
        metadataDict
    }: {
        metadataDict: CaptionView['metadata_dict'];
    } = $props();

    const score = $derived.by(() => {
        const value = metadataDict?.data?.[CAPTION_SEGMENT_MATCH_SCORE_KEY];
        return typeof value === 'number' ? value : null;
    });
</script>

{#if score !== null}
    <Badge variant="secondary" class="w-fit" data-testid="caption-match-score">
        Match {score.toFixed(3)}
    </Badge>
{/if}
