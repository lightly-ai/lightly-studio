<script lang="ts">
    import type { CaptionView } from '$lib/api/lightly_studio_local';
    import { Badge } from '$lib/components/ui/badge/index.js';
    import {
        getCaptionRepeatGroupId,
        getCaptionRepeatMaxSimilarity,
        getRepeatGroupColors
    } from '$lib/utils';

    const {
        metadataDict
    }: {
        metadataDict: CaptionView['metadata_dict'];
    } = $props();

    const groupId = $derived(getCaptionRepeatGroupId(metadataDict));
    const maxSimilarity = $derived(getCaptionRepeatMaxSimilarity(metadataDict));
    const groupColor = $derived(
        groupId !== null ? getRepeatGroupColors(groupId).color : null
    );
</script>

{#if groupId !== null || maxSimilarity !== null}
    <div class="flex flex-wrap gap-1.5" data-testid="caption-repetition-meta">
        {#if groupId !== null}
            <Badge
                variant="outline"
                class="w-fit gap-1.5 border-transparent bg-secondary/80"
                title="Captions sharing this id are a repeated-action group within the video"
                data-testid="caption-repeat-group"
                data-repeat-group={groupId}
            >
                {#if groupColor}
                    <span
                        class="size-2 shrink-0 rounded-full"
                        style="background-color: {groupColor}"
                        aria-hidden="true"
                        data-testid="caption-repeat-group-dot"
                    ></span>
                {/if}
                Repeat G{groupId}
            </Badge>
        {/if}
        {#if maxSimilarity !== null}
            <Badge
                variant="outline"
                class="w-fit border-transparent bg-secondary/80"
                title="Highest caption-text cosine similarity to another caption in this video"
                data-testid="caption-repeat-max-sim"
            >
                Max sim {maxSimilarity.toFixed(3)}
            </Badge>
        {/if}
    </div>
{/if}
