<script lang="ts">
    import type { CaptionView } from '$lib/api/lightly_studio_local';
    import { Badge } from '$lib/components/ui/badge/index.js';
    import {
        getCaptionMatchScore,
        getMatchScoreBand,
        getSimilarityColor
    } from '$lib/utils';

    const {
        metadataDict
    }: {
        metadataDict: CaptionView['metadata_dict'];
    } = $props();

    const score = $derived(getCaptionMatchScore(metadataDict));
    const band = $derived(score !== null ? getMatchScoreBand(score) : null);
    const bandLabel = $derived(
        band === 'low' ? 'Low' : band === 'medium' ? 'Med' : band === 'high' ? 'High' : null
    );
</script>

{#if score !== null && bandLabel !== null}
    <Badge
        variant="outline"
        class="w-fit gap-1.5 border-transparent bg-secondary/80"
        title="Cosine similarity between caption and video segment embedding (0–1)"
        data-testid="caption-match-score"
        data-match-band={band}
    >
        <span
            class="size-2 shrink-0 rounded-full"
            style="background-color: {getSimilarityColor(score)}"
            aria-hidden="true"
            data-testid="caption-match-score-dot"
        ></span>
        Match {score.toFixed(3)}
        <span class="text-muted-foreground">· {bandLabel}</span>
    </Badge>
{/if}
